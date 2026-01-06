import React, { useState, useEffect } from 'react';
import { KeywordItem, ProductContext, RelevanceStatus } from '../types';
import { Check, X, ArrowRight, Download, RefreshCw, ThumbsUp, ThumbsDown } from 'lucide-react';
import * as XLSX from 'xlsx';

interface ReviewInterfaceProps {
  initialKeywords: KeywordItem[];
  productContext: ProductContext;
}

export const ReviewInterface: React.FC<ReviewInterfaceProps> = ({
  initialKeywords,
  productContext
}) => {
  const [keywords, setKeywords] = useState<KeywordItem[]>(initialKeywords);
  const [activeTab, setActiveTab] = useState<'review' | 'all'>('review');
  
  // Filter for the "Review Queue" (Medium relevance)
  const reviewQueue = keywords.filter(k => k.status === RelevanceStatus.MEDIUM_RELEVANCE);
  const [currentIndex, setCurrentIndex] = useState(0);

  const currentCard = reviewQueue[currentIndex];

  const handleDecision = (approved: boolean) => {
    if (!currentCard) return;

    setKeywords(prev => prev.map(k => {
      if (k.id === currentCard.id) {
        return { ...k, status: approved ? RelevanceStatus.APPROVED : RelevanceStatus.REJECTED };
      }
      return k;
    }));

    // Move to next card (or stay at 0 since the array shrinks if we filtered, but we are filtering by status derived from state)
    // Actually, since we filter `keywords` dynamically, `reviewQueue` changes.
    // If we change the status of the item at index 0, the next item becomes index 0.
    // So we keep currentIndex at 0.
  };

  const handleExport = () => {
    const data = keywords.map(k => ({
      Keyword: k.originalText,
      Score: k.score,
      Status: k.status,
      Reasoning: k.reasoning
    }));

    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Results");
    XLSX.writeFile(wb, "keyword_analysis_results.xlsx");
  };

  const stats = {
    approved: keywords.filter(k => k.status === RelevanceStatus.APPROVED || k.status === RelevanceStatus.HIGH_RELEVANCE || k.status === RelevanceStatus.MACHINE_VERIFIED).length,
    rejected: keywords.filter(k => k.status === RelevanceStatus.REJECTED || k.status === RelevanceStatus.LOW_RELEVANCE).length,
    pending: reviewQueue.length
  };

  return (
    <div className="w-full max-w-7xl mx-auto h-[calc(100vh-100px)] flex flex-col gap-6">
      {/* Header Stats */}
      <div className="grid grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-100">
          <p className="text-xs text-slate-500 uppercase font-bold">Total Processed</p>
          <p className="text-2xl font-bold text-slate-800">{keywords.length}</p>
        </div>
        <div className="bg-indigo-50 p-4 rounded-xl shadow-sm border border-indigo-100">
          <p className="text-xs text-indigo-500 uppercase font-bold">Ready / Approved</p>
          <p className="text-2xl font-bold text-indigo-700">{stats.approved}</p>
        </div>
        <div className="bg-amber-50 p-4 rounded-xl shadow-sm border border-amber-100">
          <p className="text-xs text-amber-500 uppercase font-bold">Needs Manual Review</p>
          <p className="text-2xl font-bold text-amber-700">{stats.pending}</p>
        </div>
        <button 
          onClick={handleExport}
          className="bg-green-600 hover:bg-green-700 text-white p-4 rounded-xl shadow-md transition flex flex-col items-center justify-center"
        >
          <Download className="mb-1" size={20} />
          <span className="font-bold">Export Excel</span>
        </button>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
        
        {/* Left: Product Context (Sticky) */}
        <div className="lg:col-span-3 bg-white rounded-2xl shadow-lg border border-slate-200 p-4 overflow-y-auto">
           <h3 className="font-bold text-slate-700 mb-4 border-b pb-2">Product Context</h3>
           {/* Added data prefix to src */}
           <img 
             src={productContext.imageData ? `data:image/jpeg;base64,${productContext.imageData}` : ""} 
             className="w-full rounded-lg mb-4 shadow-sm" 
             alt="Context"
           />
           <p className="text-sm text-slate-600 mb-2 font-medium">{productContext.category}</p>
           <p className="text-xs text-slate-500">{productContext.description}</p>
        </div>

        {/* Center: Active Review Card */}
        <div className="lg:col-span-5 flex flex-col">
            <div className="flex gap-2 mb-4">
              <button 
                onClick={() => setActiveTab('review')}
                className={`flex-1 py-2 rounded-lg font-medium transition ${activeTab === 'review' ? 'bg-indigo-600 text-white shadow-md' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
              >
                Review Queue ({reviewQueue.length})
              </button>
              <button 
                 onClick={() => setActiveTab('all')}
                 className={`flex-1 py-2 rounded-lg font-medium transition ${activeTab === 'all' ? 'bg-indigo-600 text-white shadow-md' : 'bg-white text-slate-600 hover:bg-slate-50'}`}
              >
                All Keywords
              </button>
            </div>

            {activeTab === 'review' ? (
               <div className="flex-1 bg-white rounded-3xl shadow-xl border border-slate-200 p-8 flex flex-col items-center justify-center relative overflow-hidden">
                 {currentCard ? (
                   <>
                     <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-amber-400 to-indigo-500"></div>
                     <div className="text-center mb-8">
                       <span className="inline-block px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-bold mb-4">
                         Score: {currentCard.score}
                       </span>
                       <h2 className="text-4xl font-extrabold text-slate-900 mb-4">{currentCard.originalText}</h2>
                       <p className="text-slate-500 italic max-w-md">"{currentCard.reasoning}"</p>
                     </div>

                     <div className="flex gap-6 mt-8">
                       <button 
                        onClick={() => handleDecision(false)}
                        className="w-20 h-20 rounded-full bg-slate-100 hover:bg-red-100 text-slate-400 hover:text-red-600 transition flex items-center justify-center border-2 border-slate-200 hover:border-red-300"
                        title="Reject"
                       >
                         <X size={32} strokeWidth={3} />
                       </button>
                       <button 
                        onClick={() => handleDecision(true)}
                        className="w-24 h-24 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-xl hover:shadow-2xl transition flex items-center justify-center transform hover:scale-105"
                        title="Approve"
                       >
                         <Check size={40} strokeWidth={3} />
                       </button>
                     </div>
                     <p className="text-xs text-slate-400 mt-8">Keyboard shortcuts: Left (Reject), Right (Approve)</p>
                   </>
                 ) : (
                   <div className="text-center">
                     <Check className="w-20 h-20 text-green-500 mx-auto mb-4" />
                     <h3 className="text-2xl font-bold text-slate-800">Queue Empty!</h3>
                     <p className="text-slate-500 mt-2">All uncertain keywords have been reviewed.</p>
                   </div>
                 )}
               </div>
            ) : (
              <div className="flex-1 bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden flex flex-col">
                  <div className="p-4 border-b bg-slate-50 font-bold text-slate-700 grid grid-cols-12 gap-2 text-sm">
                    <div className="col-span-6">Keyword</div>
                    <div className="col-span-2">Score</div>
                    <div className="col-span-4">Status</div>
                  </div>
                  <div className="flex-1 overflow-y-auto p-2 space-y-1">
                    {keywords.map(k => (
                      <div key={k.id} className="grid grid-cols-12 gap-2 p-3 hover:bg-slate-50 rounded-lg text-sm border-b border-slate-50 items-center">
                        <div className="col-span-6 font-medium text-slate-800">{k.originalText}</div>
                        <div className="col-span-2 text-slate-500">{k.score}</div>
                        <div className="col-span-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                            k.status === RelevanceStatus.APPROVED || k.status === RelevanceStatus.HIGH_RELEVANCE || k.status === RelevanceStatus.MACHINE_VERIFIED
                              ? 'bg-green-100 text-green-700'
                              : k.status === RelevanceStatus.REJECTED || k.status === RelevanceStatus.LOW_RELEVANCE
                              ? 'bg-red-100 text-red-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}>
                            {k.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
              </div>
            )}
        </div>

        {/* Right: Quick List (Approved) */}
        <div className="lg:col-span-4 bg-white rounded-2xl shadow-lg border border-slate-200 p-4 flex flex-col min-h-0">
           <h3 className="font-bold text-slate-700 mb-4 flex items-center justify-between">
             <span>Approved List</span>
             <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">{stats.approved}</span>
           </h3>
           <div className="flex-1 overflow-y-auto space-y-2 pr-2">
             {keywords.filter(k => k.status === RelevanceStatus.APPROVED || k.status === RelevanceStatus.HIGH_RELEVANCE || k.status === RelevanceStatus.MACHINE_VERIFIED).map(k => (
               <div key={k.id} className="p-3 bg-slate-50 rounded-lg border border-slate-100 flex justify-between items-start group hover:bg-indigo-50 transition">
                 <div>
                   <p className="font-semibold text-slate-800 text-sm">{k.originalText}</p>
                   {k.status === RelevanceStatus.MACHINE_VERIFIED && (
                     <p className="text-[10px] text-blue-600 flex items-center gap-1 mt-1">
                       <RefreshCw size={10} /> Machine Verified
                     </p>
                   )}
                 </div>
                 <span className="text-xs font-mono text-slate-400">{k.score}</span>
               </div>
             ))}
           </div>
        </div>

      </div>
    </div>
  );
};