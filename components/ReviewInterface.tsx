import React, { useState, useEffect } from 'react';
import { KeywordItem, ProductContext, RelevanceStatus } from '../types';
import { api, AnalysisStatus } from '../services/api';
import { Check, X, Download, Server, CircleHelp } from 'lucide-react';
import * as XLSX from 'xlsx';

interface ReviewInterfaceProps {
  initialKeywords: KeywordItem[]; // Mostly unused now, fetched from API
  productContext: ProductContext;
}

export const ReviewInterface: React.FC<ReviewInterfaceProps> = ({
  initialKeywords,
  productContext
}) => {
  // State for tabs
  const [activeTab, setActiveTab] = useState<'review' | 'all'>('review');
  const [allKeywords, setAllKeywords] = useState<any[]>([]);

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

      // Fetch all keywords occasionaly or every time?
      const all = await api.getAllKeywords();
      setAllKeywords(all);

      setIsConnected(true);
    } catch (e) {
      setIsConnected(false);
    }
  };

  // Initial load & Polling
  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 3000); // Polling for updates (optional if we drive everything locally)

    // Trigger initial browser open - DISABLED
    // api.navigateTo(0).catch(() => { });

    return () => clearInterval(interval);
  }, []);

  const currentCard = reviewQueue[currentIndex];

  const handleDecision = async (decision: 'keep' | 'delete' | 'undecided') => {
    if (!currentCard) return;

    try {
      await api.performAction(decision, currentIndex);
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
    pending: reviewQueue.filter(k => k.status === 'pending').length
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
            <p className="mb-3">Browser window requires manual launch:</p>
            <button
              onClick={() => api.openBrowser()}
              className="w-full bg-slate-800 hover:bg-slate-900 text-white py-2 px-4 rounded-lg mb-3 flex items-center justify-center gap-2 transition shadow-sm"
            >
              <Server size={14} /> Open Browser
            </button>
            <p className="text-indigo-600 italic">Clicking Approve/Reject will verify your choice and automatically navigate the browser to the next product.</p>
          </div>
        </div>

        {/* Center: Tabs & Review/History */}
        <div className="lg:col-span-5 flex flex-col h-full">
          {/* Tabs Header */}
          <div className="flex items-center gap-2 mb-4 bg-white p-1 rounded-xl shadow-sm border border-slate-100 w-fit">
            <button
              onClick={() => setActiveTab('review')}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition ${activeTab === 'review' ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-50'}`}
            >Review Queue ({reviewQueue.length})</button>
            <button
              onClick={() => setActiveTab('all')}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition ${activeTab === 'all' ? 'bg-indigo-600 text-white' : 'text-slate-500 hover:bg-slate-50'}`}
            >History</button>
          </div>

          {/* Tab Content */}
          <div className={`flex-1 ${activeTab === 'review' ? 'block' : 'hidden'} flex flex-col`}>
            <div className="flex-1 bg-white rounded-3xl shadow-xl border border-slate-200 p-8 flex flex-col relative overflow-hidden">
              {currentCard ? (
                <>
                  <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-amber-400 to-indigo-500"></div>

                  {/* Content Area - Flexible height to absorb size changes */}
                  <div className="flex-1 flex flex-col items-center justify-center min-h-0">
                    <div className="text-center w-full">
                      <span className="inline-block px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-bold mb-4">
                        Score: {currentCard.score?.toFixed(3)}
                      </span>
                      {currentCard.status !== 'pending' && (
                        <span className={`block mt-2 text-xs font-bold uppercase ${currentCard.status === 'kept' ? 'text-green-600' :
                          currentCard.status === 'deleted' ? 'text-red-600' : 'text-amber-600'
                          }`}>
                          {currentCard.status}
                        </span>
                      )}

                      {/* Fixed height container for text to further stabilize? Or just flex-center is enough.
                          Let's trust flex-1 center, but maybe add explicit height limits or overflow handling if needed. 
                      */}
                      <h2 className="text-4xl font-extrabold text-slate-900 mb-4 px-4 leading-tight">
                        {currentCard.keyword}
                      </h2>
                      <p className="text-slate-400 text-sm">Reviewing {currentIndex + 1} of {reviewQueue.length}</p>
                    </div>
                  </div>

                  {/* Buttons Area - Fixed height footer */}
                  <div className="h-32 flex-shrink-0 flex gap-6 items-center justify-center border-t border-slate-50 mt-4 pt-4">
                    <button
                      onClick={() => handleDecision('delete')}
                      className="w-20 h-20 rounded-full bg-slate-100 hover:bg-red-100 text-slate-400 hover:text-red-600 transition flex items-center justify-center border-2 border-slate-200 hover:border-red-300"
                      title="Delete"
                    >
                      <X size={32} strokeWidth={3} />
                    </button>

                    <button
                      onClick={() => handleDecision('undecided')}
                      className="w-20 h-20 rounded-full bg-amber-50 hover:bg-amber-100 text-slate-400 hover:text-amber-600 transition flex items-center justify-center border-2 border-slate-200 hover:border-amber-300 font-bold text-lg"
                      title="Undecided"
                    >
                      <CircleHelp size={32} strokeWidth={3} />
                    </button>

                    <button
                      onClick={() => handleDecision('keep')}
                      className="w-20 h-20 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-xl hover:shadow-2xl transition flex items-center justify-center transform hover:scale-105"
                      title="Keep"
                    >
                      <Check size={32} strokeWidth={3} />
                    </button>
                  </div>
                </>
              ) : (
                <div className="text-center flex-1 flex flex-col items-center justify-center">
                  <Check className="w-20 h-20 text-green-500 mx-auto mb-4" />
                  <h3 className="text-2xl font-bold text-slate-800">Review Complete!</h3>
                  <p className="text-slate-500 mt-2">No more pending items in the manual queue.</p>
                </div>
              )}
            </div>
          </div>

          <div className={`flex-1 ${activeTab === 'all' ? 'block' : 'hidden'} bg-white rounded-2xl shadow-lg border border-slate-200 p-4 flex flex-col min-h-0 overflow-y-auto`}>
            <div className="space-y-2 pr-2">
              {/* Stack structure (Newest/Last Modified on Top) - approximated by reversing the manual queue processed items? Or just showing the history stack as requested. */}
              {/* The user requested "History" to be moved here. History was previously filtered by status != pending. */}
              {reviewQueue.filter(k => k.status !== 'pending').reverse().map((k, i) => (
                <div key={i} className={`p-3 rounded-lg text-sm flex justify-between items-center ${k.status === 'kept' ? 'bg-green-50 text-green-800' :
                  k.status === 'undecided' ? 'bg-amber-50 text-amber-800' :
                    'bg-red-50 text-red-800'
                  }`}>
                  <span className="font-bold">{k.keyword}</span>
                  <span className="uppercase text-xs font-bold">{k.status}</span>
                </div>
              ))}
              {reviewQueue.filter(k => k.status !== 'pending').length === 0 && (
                <p className="text-center text-slate-400 py-10">No history yet.</p>
              )}
            </div>
          </div>

        </div>

        {/* Right: All Keywords List (Scrollable) */}
        <div className="lg:col-span-4 bg-white rounded-2xl shadow-lg border border-slate-200 p-4 flex flex-col min-h-0 h-full">
          <h3 className="font-bold text-slate-700 mb-4 flex justify-between items-center">
            <span>All Keywords List</span>
            <span className="bg-slate-100 text-slate-500 px-2 py-1 rounded text-xs">{allKeywords.length}</span>
          </h3>
          <div className="flex-1 overflow-y-auto space-y-1 pr-1 custom-scrollbar">
            {allKeywords.map((k, i) => (
              <div key={i} title={k.reason ? `${k.keyword}\nReason: ${k.reason}` : k.keyword}
                className={`p-2 rounded text-xs flex justify-between items-center transition-all ${k.status === 'kept' || k.status === 'verified_keep' ? 'bg-emerald-100/80 text-emerald-900 border-l-4 border-emerald-500' :
                  k.status === 'deleted' || k.status === 'verified_delete' ? 'bg-rose-100/80 text-rose-900 border-l-4 border-rose-500' :
                    k.status === 'undecided' ? 'bg-amber-100/80 text-amber-900 border-l-4 border-amber-500' :
                      k.status === 'AUTO' ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-400 animate-pulse' :
                        'bg-slate-50 border-l-4 border-transparent text-slate-500'
                  } mb-1`}>
                <span className="truncate flex-1 mr-2">
                  {k.keyword}
                  {(k.status === 'verified_keep' || k.status === 'verified_delete') && (
                    <span className="ml-1 text-[10px] opacity-70 border border-current px-1 rounded flex items-center gap-1 inline-flex">
                      AI
                      {k.similar_count !== undefined && <span title="Similar Products Found">({k.similar_count})</span>}
                      {k.vision_score !== undefined && <span title="Vision Confidence">{(k.vision_score * 100).toFixed(0)}%</span>}
                    </span>
                  )}
                  {k.status === 'AUTO' && <span className="ml-1 text-[10px]">Processing...</span>}
                </span>
                <span className="text-slate-400 w-8 text-right">{Math.round((k.score || 0) * 100)}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
};