import React, { useEffect, useRef, useState } from 'react';
import { analyzeProductImage } from '../services/gemini';
import { api, AnalysisStatus } from '../services/api';
import { KeywordItem, ProductContext, RelevanceStatus } from '../types';
import { generateId } from '../utils';
import { Play, Pause, FastForward, CheckCircle2, Save, FileDown, Server } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import * as XLSX from 'xlsx';

const SESSION_KEY = 'keyword_lens_session';

interface ProcessingDashboardProps {
  initialKeywords: string[];
  initialProcessed?: KeywordItem[]; // For resume functionality
  productImageBase64: string;
  imageFile: File;
  excelFile: File | null;
  onAnalysisComplete: (results: KeywordItem[], ctx: ProductContext) => void;
}

export const ProcessingDashboard: React.FC<ProcessingDashboardProps> = ({
  initialKeywords,
  initialProcessed = [],
  productImageBase64,
  imageFile,
  excelFile,
  onAnalysisComplete
}) => {
  const [status, setStatus] = useState<'analyzing_image' | 'starting_backend' | 'polling' | 'paused' | 'done'>('analyzing_image');
  const [productContext, setProductContext] = useState<ProductContext | null>(null);
  const [backendStatus, setBackendStatus] = useState<AnalysisStatus | null>(null);
  const [logs, setLogs] = useState<string[]>([]);

  const isPausedRef = useRef(false);

  const hasStartedBackendRef = useRef(false);

  const addLog = (msg: string) => setLogs(prev => [msg, ...prev].slice(0, 50));

  const hasStartedAnalysisRef = useRef(false);

  // 1. Analyze Image (Client-side Gemini)
  useEffect(() => {
    const startImageAnalysis = async () => {
      if (hasStartedAnalysisRef.current) return;
      hasStartedAnalysisRef.current = true;

      try {
        addLog('Starting visual analysis of product (Gemini)...');
        const analysis = await analyzeProductImage(productImageBase64);

        const ctx: ProductContext = {
          imageFile,
          imageData: productImageBase64,
          description: analysis.description,
          category: analysis.category,
          visualFeatures: analysis.features
        };

        setProductContext(ctx);
        addLog(`Image Analyzed: ${analysis.category}`);

        // Only advance status if we haven't moved past it (though usually we wouldn't have)
        setStatus(s => s === 'analyzing_image' ? 'starting_backend' : s);

      } catch (err) {
        addLog(`Error analyzing image: ${err}`);
        hasStartedAnalysisRef.current = false; // Allow retry on error
      }
    };

    if (status === 'analyzing_image') {
      startImageAnalysis();
    }
  }, [productImageBase64, imageFile, status]);

  // 2. Start Backend Analysis
  useEffect(() => {
    const startBackend = async () => {
      if (status !== 'starting_backend' || !productContext) return;
      if (hasStartedBackendRef.current) return; // Prevent double call

      hasStartedBackendRef.current = true;

      try {
        // Upload Excel first if available
        if (excelFile) {
          addLog('Uploading Excel to backend for persistence...');
          await api.uploadExcel(excelFile);
          addLog('Excel uploaded successfully.');
        }

        addLog('Sending data to Python Backend...');
        const response = await api.analyze(initialKeywords, productContext.description);
        addLog(`Backend initiated: ${JSON.stringify(response)}`);

        setStatus('polling');
        addLog('Status switched to POLLING');
      } catch (e) {
        addLog(`Error connecting to backend: ${e}`);
        addLog('Make sure server.py is running on port 8000');
        hasStartedBackendRef.current = false; // Reset on error
      }
    };

    startBackend();
  }, [status, productContext, initialKeywords, excelFile]);

  // 3. Poll Backend Status
  useEffect(() => {
    if (status !== 'polling') return;

    addLog('Starting Polling Interval...');

    const interval = setInterval(async () => {
      if (isPausedRef.current) {
        // addLog('Polling paused...'); // Too noisy
        return;
      }

      // addLog('Polling...'); // Debug only

      try {
        const s = await api.getStatus();
        setBackendStatus(s);

        // Check if done (simple heuristic: manual + auto == total, or status message)
        // Here we just rely on the backend status or counts. 
        // Let's assume if we have results in queues, we show stats.

        // Logic to detect completion could be handled by backend status string
        const total = s.manual_count + s.auto_count + s.excluded_count;
        if (s.status.includes('Scoring Complete') || total === initialKeywords.length) {
          setStatus('done');
          addLog('Scoring phase complete.');
        }

      } catch (e) {
        console.error("Polling error", e);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [status, initialKeywords.length]);

  const togglePause = () => {
    isPausedRef.current = !isPausedRef.current;
    if (isPausedRef.current) setStatus('paused');
    else setStatus('polling');
  };

  // Convert backend stats to Chart Data
  const chartData = [
    { name: 'Manual Review', value: backendStatus?.manual_count || 0, color: '#fbbf24' }, // Amber
    { name: 'Machine Auto', value: backendStatus?.auto_count || 0, color: '#3b82f6' },   // Blue
    { name: 'Excluded', value: backendStatus?.excluded_count || 0, color: '#94a3b8' },   // Slate (Gray)
  ];

  const totalProcessed = (backendStatus?.manual_count || 0) + (backendStatus?.auto_count || 0) + (backendStatus?.excluded_count || 0);
  const progress = Math.min(100, (totalProcessed / initialKeywords.length) * 100);

  // NOTE: Removed full-page "Done" view to keep the dashboard visible as per user request.
  // if (status === 'done' && productContext) { return ... }

  return (
    <div className="w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Col: Context */}
      <div className="lg:col-span-1 bg-white rounded-2xl shadow-lg p-6 border border-slate-100 flex flex-col h-[600px]">
        <h3 className="text-lg font-bold text-slate-800 mb-4">Live Context</h3>
        {productContext ? (
          <div className="space-y-4 flex-1 overflow-y-auto">
            <img
              src={`data:image/jpeg;base64,${productContext.imageData}`}
              alt="Product"
              className="w-full h-48 object-cover rounded-lg shadow-sm border border-slate-100"
            />
            <div>
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Category</span>
              <p className="text-sm font-medium text-slate-800">{productContext.category}</p>
            </div>
            <div>
              <span className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Analysis</span>
              <p className="text-xs text-slate-600 leading-relaxed">{productContext.description}</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-slate-400">
            Analyzing Image...
          </div>
        )}

        <div className="mt-6 pt-6 border-t border-slate-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-600">Progress</span>
            <span className="text-sm font-bold text-indigo-600">{Math.round(progress)}%</span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-2.5 mb-4">
            <div className="bg-indigo-600 h-2.5 rounded-full transition-all duration-500" style={{ width: `${progress}%` }}></div>
          </div>

          <div className="flex items-center justify-center gap-2 text-xs text-slate-500">
            <Server size={12} /> Backend Mode: {backendStatus?.status || 'Connecting...'}
          </div>
        </div>
      </div>

      {/* Middle: Logs */}
      <div className="lg:col-span-1 bg-slate-900 rounded-2xl shadow-lg p-6 flex flex-col h-[600px]">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <FastForward className="text-green-400" /> System Logs
        </h3>
        <div className="flex-1 overflow-y-auto font-mono text-xs space-y-2 pr-2">
          {logs.map((log, i) => (
            <div key={i} className="text-slate-300 border-l-2 border-slate-700 pl-2">
              <span className="text-slate-500">{new Date().toLocaleTimeString()}</span> {log}
            </div>
          ))}
        </div>
      </div>

      {/* Right: Stats */}
      <div className="lg:col-span-1 bg-white rounded-2xl shadow-lg p-6 border border-slate-100 h-[600px] flex flex-col">
        <h3 className="text-lg font-bold text-slate-800 mb-4">Live Queue Distribution</h3>
        <div className="flex-1 relative w-full min-h-0">
          <div className="absolute inset-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center">
              <span className="block text-3xl font-bold text-slate-800">{totalProcessed}</span>
              <span className="text-xs text-slate-500">Scored</span>
            </div>
          </div>
        </div>

        {/* Buttons in Right Column */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex flex-col gap-3">
          <button
            onClick={() => api.exportResults()}
            disabled={status !== 'done'}
            className={`w-full px-4 py-3 rounded-xl font-bold transition shadow-md justify-center ${status === 'done'
              ? 'bg-indigo-600 text-white hover:bg-indigo-700'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              }`}
          >
            <FileDown size={18} />
            下载 excel
          </button>
          <button
            onClick={() => onAnalysisComplete([], productContext!)}
            disabled={status !== 'done'}
            className={`w-full px-4 py-3 rounded-xl font-bold transition shadow-md ${status === 'done'
              ? 'bg-indigo-600 text-white hover:bg-indigo-700'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed'
              }`}
          >
            Start Hybrid Review
          </button>
        </div>
      </div>
    </div>
  );
};