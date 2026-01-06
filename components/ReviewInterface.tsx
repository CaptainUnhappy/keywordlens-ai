import React, { useState, useEffect } from 'react';
import { KeywordItem, ProductContext, RelevanceStatus } from '../types';
import { api, AnalysisStatus } from '../services/api';
import { Check, X, Download, Server } from 'lucide-react';
import * as XLSX from 'xlsx';

interface ReviewInterfaceProps {
  initialKeywords: KeywordItem[]; // Mostly unused now, fetched from API
  productContext: ProductContext;
}

export const ReviewInterface: React.FC<ReviewInterfaceProps> = ({
  initialKeywords,
  productContext
}) => {
  // We'll manage state via the backend
  const [reviewQueue, setReviewQueue] = useState<any[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isConnected, setIsConnected] = useState(true);

  // Sync state with backend
  const fetchState = async () => {
    try {
      const status = await api.getStatus();
      setCurrentIndex(status.current_manual_index);

      const queue = await api.getManualQueue();
      setReviewQueue(queue);
      setIsConnected(true);
    } catch (e) {
      setIsConnected(false);
    }
  };

  // Initial load & Polling
  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 1000); // Polling for updates (optional if we drive everything locally)

    // Trigger initial browser open
    api.navigateTo(0).catch(() => { });

    return () => clearInterval(interval);
  }, []);

  const currentCard = reviewQueue[currentIndex];

  const handleDecision = async (approved: boolean) => {
    if (!currentCard) return;

    try {
      await api.performAction(approved ? 'keep' : 'delete', currentIndex);
      // Optimistic update
      // setCurrentIndex(prev => prev + 1); // Backend handles logic
      fetchState(); // Sync immediately
    } catch (e) {
      alert("Failed to communicate with backend");
    }
  };


  const stats = {
    approved: reviewQueue.filter(k => k.status === 'kept').length,
    rejected: reviewQueue.filter(k => k.status === 'deleted').length,
    pending: reviewQueue.filter(k => k.status === 'pending_MANUAL').length
  };

  return (
    <div className="w-full max-w-7xl mx-auto h-[calc(100vh-100px)] flex flex-col gap-6">
      {/* Header Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-500 uppercase font-bold">In Manual Queue</p>
            <p className="text-2xl font-bold text-slate-800">{reviewQueue.length}</p>
          </div>
          {!isConnected && <span className="text-xs text-red-500 bg-red-50 px-2 py-1 rounded">Disconnected</span>}
        </div>
        <div className="bg-green-50 p-4 rounded-xl shadow-sm border border-green-100">
          <p className="text-xs text-green-600 uppercase font-bold">Kept</p>
          <p className="text-2xl font-bold text-green-700">{stats.approved}</p>
        </div>
        <div className="bg-red-50 p-4 rounded-xl shadow-sm border border-red-100">
          <p className="text-xs text-red-600 uppercase font-bold">Deleted</p>
          <p className="text-2xl font-bold text-red-700">{stats.rejected}</p>
        </div>
        <button
          onClick={() => api.exportResults()}
          className="bg-indigo-600 hover:bg-indigo-700 text-white p-4 rounded-xl shadow-md transition flex flex-col items-center justify-center"
        >
          <Download className="mb-1" size={20} />
          <span className="font-bold">Export Excel</span>
        </button>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">

        {/* Left: Product Context (Sticky) */}
        <div className="lg:col-span-3 bg-white rounded-2xl shadow-lg border border-slate-200 p-4 overflow-y-auto">
          <h3 className="font-bold text-slate-700 mb-4 border-b pb-2">Product Context</h3>
          <img
            src={productContext.imageData ? `data:image/jpeg;base64,${productContext.imageData}` : ""}
            className="w-full rounded-lg mb-4 shadow-sm"
            alt="Context"
          />
          <p className="text-sm text-slate-600 mb-2 font-medium">{productContext.category}</p>
          <p className="text-xs text-slate-500">{productContext.description}</p>

          <div className="mt-8 bg-slate-50 p-4 rounded-lg text-xs text-slate-500 border border-slate-200">
            <strong className="block mb-2 text-slate-700 flex items-center gap-2"><Server size={12} /> Browser Control</strong>
            <p>Your screen should now show a browser window controlled by the backend.</p>
            <p className="mt-2 text-indigo-600 italic">Clicking Approve/Reject will verify your choice and automatically navigate the browser to the next product.</p>
          </div>
        </div>

        {/* Center: Active Review Card */}
        <div className="lg:col-span-6 flex flex-col">
          <div className="flex-1 bg-white rounded-3xl shadow-xl border border-slate-200 p-8 flex flex-col items-center justify-center relative overflow-hidden">
            {currentCard ? (
              <>
                <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-amber-400 to-indigo-500"></div>
                <div className="text-center mb-8">
                  <span className="inline-block px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-bold mb-4">
                    Score: {currentCard.score?.toFixed(3)}
                  </span>
                  {currentCard.status !== 'pending_MANUAL' && (
                    <span className={`block mt-2 text-xs font-bold uppercase ${currentCard.status === 'kept' ? 'text-green-600' : 'text-red-600'}`}>
                      {currentCard.status}
                    </span>
                  )}
                  <h2 className="text-4xl font-extrabold text-slate-900 mb-4">{currentCard.keyword}</h2>
                  <p className="text-slate-400 text-sm">Reviewing {currentIndex + 1} of {reviewQueue.length}</p>
                </div>

                <div className="flex gap-6 mt-8">
                  <button
                    onClick={() => handleDecision(false)}
                    className="w-20 h-20 rounded-full bg-slate-100 hover:bg-red-100 text-slate-400 hover:text-red-600 transition flex items-center justify-center border-2 border-slate-200 hover:border-red-300"
                    title="Delete"
                  >
                    <X size={32} strokeWidth={3} />
                  </button>
                  <button
                    onClick={() => handleDecision(true)}
                    className="w-24 h-24 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-xl hover:shadow-2xl transition flex items-center justify-center transform hover:scale-105"
                    title="Keep"
                  >
                    <Check size={40} strokeWidth={3} />
                  </button>
                </div>
              </>
            ) : (
              <div className="text-center">
                <Check className="w-20 h-20 text-green-500 mx-auto mb-4" />
                <h3 className="text-2xl font-bold text-slate-800">Review Complete!</h3>
                <p className="text-slate-500 mt-2">No more pending items in the manual queue.</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: History */}
        <div className="lg:col-span-3 bg-white rounded-2xl shadow-lg border border-slate-200 p-4 flex flex-col min-h-0">
          <h3 className="font-bold text-slate-700 mb-4">History</h3>
          <div className="flex-1 overflow-y-auto space-y-2 pr-2">
            {reviewQueue.filter(k => k.status !== 'pending_MANUAL').reverse().map((k, i) => (
              <div key={i} className={`p-2 rounded-lg text-xs flex justify-between ${k.status === 'kept' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                <span className="font-medium">{k.keyword}</span>
                <span>{k.status}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};