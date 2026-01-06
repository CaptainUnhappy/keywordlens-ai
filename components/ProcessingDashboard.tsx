import React, { useEffect, useRef, useState } from 'react';
import { analyzeProductImage, batchScoreKeywords, machineVerifyKeyword } from '../services/gemini';
import { KeywordItem, ProductContext, RelevanceStatus } from '../types';
import { generateId } from '../utils';
import { Play, Pause, FastForward, CheckCircle2, AlertCircle, Save, FileDown } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import * as XLSX from 'xlsx';

const SESSION_KEY = 'keyword_lens_session';

interface ProcessingDashboardProps {
  initialKeywords: string[];
  initialProcessed?: KeywordItem[]; // For resume functionality
  productImageBase64: string;
  imageFile: File;
  onAnalysisComplete: (results: KeywordItem[], ctx: ProductContext) => void;
}

export const ProcessingDashboard: React.FC<ProcessingDashboardProps> = ({
  initialKeywords,
  initialProcessed = [],
  productImageBase64,
  imageFile,
  onAnalysisComplete
}) => {
  const [status, setStatus] = useState<'analyzing_image' | 'processing_keywords' | 'paused' | 'done'>('analyzing_image');
  const [productContext, setProductContext] = useState<ProductContext | null>(null);
  // Initialize with restored items if available
  const [processedKeywords, setProcessedKeywords] = useState<KeywordItem[]>(initialProcessed);
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  
  // Processing Refs
  // Filter out keywords that have already been processed to avoid duplicates/re-work
  const queueRef = useRef<string[]>(
    initialKeywords.filter(k => !initialProcessed.some(pk => pk.originalText === k))
  );
  
  const isPausedRef = useRef(false);
  
  const BATCH_SIZE = 10;

  const addLog = (msg: string) => setLogs(prev => [msg, ...prev].slice(0, 50));

  // Auto-Save Logic
  useEffect(() => {
    if (processedKeywords.length > 0 && productContext) {
        try {
            const sessionData = {
                rawKeywords: initialKeywords,
                processedKeywords: processedKeywords,
                imageBase64: productImageBase64,
                productContext: productContext,
                timestamp: new Date().toISOString()
            };
            localStorage.setItem(SESSION_KEY, JSON.stringify(sessionData));
            setLastSaved(new Date());
        } catch (e) {
            console.warn("Auto-save failed (likely quota exceeded)", e);
        }
    }
  }, [processedKeywords, productContext, initialKeywords, productImageBase64]);

  // 1. Analyze Image (Skip if we already have context from restore)
  useEffect(() => {
    const startImageAnalysis = async () => {
      // If we restored session and have context, skip analysis
      try {
        const savedSession = localStorage.getItem(SESSION_KEY);
        if (savedSession) {
            const data = JSON.parse(savedSession);
            if (data.productContext && data.productContext.description) {
                setProductContext(data.productContext);
                addLog('Restored previous analysis context.');
                setStatus('processing_keywords');
                return;
            }
        }
      } catch (e) {}

      try {
        addLog('Starting visual analysis of product...');
        const analysis = await analyzeProductImage(productImageBase64);
        
        const ctx: ProductContext = {
          imageFile,
          imageData: productImageBase64,
          description: analysis.description,
          category: analysis.category,
          visualFeatures: analysis.features
        };
        
        setProductContext(ctx);
        addLog(`Image Analyzed: ${analysis.category} - ${analysis.description.substring(0, 50)}...`);
        setStatus('processing_keywords');
      } catch (err) {
        addLog(`Error analyzing image: ${err}`);
      }
    };

    if (status === 'analyzing_image') {
      startImageAnalysis();
    }
  }, [productImageBase64, imageFile, status]);

  // 2. Process Keywords Loop
  useEffect(() => {
    if (status !== 'processing_keywords' || !productContext) return;

    const processBatch = async () => {
      if (isPausedRef.current) return;
      
      // Update progress based on total vs remaining
      const total = initialKeywords.length;
      const remaining = queueRef.current.length;
      const currentProgress = ((total - remaining) / total) * 100;
      setProgress(currentProgress);

      if (queueRef.current.length === 0) {
        setStatus('done');
        // Final Save
        try {
            localStorage.removeItem(SESSION_KEY); // Clear recovery on natural finish, or keep it? 
            // Better to keep it until they export in the next step.
        } catch(e) {}
        return;
      }

      const batch = queueRef.current.splice(0, BATCH_SIZE);
      addLog(`Processing batch of ${batch.length} keywords...`);

      try {
        const scores = await batchScoreKeywords(batch, productContext.description);
        
        const newItems: KeywordItem[] = scores.map(s => {
          let status = RelevanceStatus.PENDING;
          if (s.score >= 80) status = RelevanceStatus.HIGH_RELEVANCE;
          else if (s.score <= 30) status = RelevanceStatus.LOW_RELEVANCE;
          else status = RelevanceStatus.MEDIUM_RELEVANCE;

          return {
            id: generateId(),
            originalText: s.keyword,
            score: s.score,
            reasoning: s.reasoning,
            status
          };
        });

        // Trigger Machine Verification for Low Relevance items
        const enhancedItems = await Promise.all(newItems.map(async (item) => {
             if (item.status === RelevanceStatus.LOW_RELEVANCE) {
                 const isActuallyRelevant = await machineVerifyKeyword(item.originalText, productContext.description, productImageBase64);
                 if (isActuallyRelevant) {
                     return { ...item, status: RelevanceStatus.MACHINE_VERIFIED, reasoning: item.reasoning + " (Recovered by Deep Check)" };
                 } else {
                     return { ...item, status: RelevanceStatus.REJECTED };
                 }
             }
             return item;
        }));

        setProcessedKeywords(prev => [...prev, ...enhancedItems]);
        
      } catch (e) {
        addLog(`Error processing batch: ${e}`);
        // Return items to queue if failed? For now we just log.
      }
      
      // Schedule next batch with a slight delay
      if (status === 'processing_keywords' && !isPausedRef.current) {
        setTimeout(processBatch, 1500); 
      }
    };

    processBatch();
  }, [status, productContext, initialKeywords.length]);


  const togglePause = () => {
    if (status === 'paused') {
      setStatus('processing_keywords');
      isPausedRef.current = false;
    } else if (status === 'processing_keywords') {
      setStatus('paused');
      isPausedRef.current = true;
    }
  };

  const handleManualExport = () => {
    const data = processedKeywords.map(k => ({
        Keyword: k.originalText,
        Score: k.score,
        Status: k.status,
        Reasoning: k.reasoning
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Partial_Results");
    XLSX.writeFile(wb, `keyword_progress_${new Date().getTime()}.xlsx`);
    addLog("Progress exported to Excel.");
  };

  const chartData = [
    { name: 'High Relevance', value: processedKeywords.filter(k => k.status === RelevanceStatus.HIGH_RELEVANCE).length, color: '#4f46e5' },
    { name: 'Needs Review', value: processedKeywords.filter(k => k.status === RelevanceStatus.MEDIUM_RELEVANCE).length, color: '#fbbf24' },
    { name: 'Machine Verified', value: processedKeywords.filter(k => k.status === RelevanceStatus.MACHINE_VERIFIED).length, color: '#3b82f6' },
    { name: 'Rejected', value: processedKeywords.filter(k => k.status === RelevanceStatus.REJECTED).length, color: '#ef4444' },
  ];

  if (status === 'done' && productContext) {
    return (
      <div className="text-center space-y-6">
        <div className="text-6xl text-green-500 mb-4 flex justify-center"><CheckCircle2 /></div>
        <h2 className="text-3xl font-bold text-slate-800">Analysis Complete!</h2>
        <p className="text-slate-600">Processed {initialKeywords.length} keywords.</p>
        <button 
          onClick={() => onAnalysisComplete(processedKeywords, productContext)}
          className="bg-indigo-600 text-white px-8 py-4 rounded-xl text-lg font-bold shadow-lg hover:bg-indigo-700 transition"
        >
          Proceed to Review
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Col: Product Context & Controls */}
      <div className="lg:col-span-1 bg-white rounded-2xl shadow-lg p-6 border border-slate-100 flex flex-col h-[600px]">
        <h3 className="text-lg font-bold text-slate-800 mb-4">Live Context</h3>
        {productContext ? (
          <div className="space-y-4 flex-1 overflow-y-auto">
            {/* Added data prefix to src */}
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
           
           <div className="grid grid-cols-2 gap-2">
             <button 
               onClick={togglePause}
               className="py-2 flex items-center justify-center gap-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition font-medium text-slate-700"
             >
               {status === 'paused' ? <><Play size={16} /> Resume</> : <><Pause size={16} /> Pause</>}
             </button>
             <button 
               onClick={handleManualExport}
               className="py-2 flex items-center justify-center gap-2 bg-indigo-50 border border-indigo-200 text-indigo-700 rounded-lg hover:bg-indigo-100 transition font-medium"
               title="Download current results to Excel"
             >
               <FileDown size={16} /> Save File
             </button>
           </div>
           {lastSaved && (
               <div className="text-center mt-2 text-[10px] text-slate-400 flex items-center justify-center gap-1">
                   <Save size={10} /> Auto-saved {lastSaved.toLocaleTimeString()}
               </div>
           )}
        </div>
      </div>

      {/* Middle Col: Logs & Current Batch */}
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

      {/* Right Col: Stats Visualization */}
      <div className="lg:col-span-1 bg-white rounded-2xl shadow-lg p-6 border border-slate-100 h-[600px] flex flex-col">
        <h3 className="text-lg font-bold text-slate-800 mb-4">Real-time Distribution</h3>
        {/* Fixed: Use flex-1 with relative positioning and absolute inner container to fix Recharts size issue */}
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
                  <span className="block text-3xl font-bold text-slate-800">{processedKeywords.length}</span>
                  <span className="text-xs text-slate-500">Keywords</span>
                </div>
             </div>
        </div>
        <div className="space-y-3 mt-4">
          {chartData.map((d) => (
            <div key={d.name} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: d.color }}></div>
                <span className="text-slate-600">{d.name}</span>
              </div>
              <span className="font-bold text-slate-800">{d.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};