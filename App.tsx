import React, { useState, useEffect } from 'react';
import { AppStep, KeywordItem, ProductContext } from './types';
import { FileUpload } from './components/FileUpload';
import { ProcessingDashboard } from './components/ProcessingDashboard';
import { ReviewInterface } from './components/ReviewInterface';
import { BrainCircuit, RotateCcw, Trash2 } from 'lucide-react';

const SESSION_KEY = 'keyword_lens_session';

const App: React.FC = () => {
  const [step, setStep] = useState<AppStep>(AppStep.UPLOAD);
  
  // App State
  const [rawKeywords, setRawKeywords] = useState<string[]>([]);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageBase64, setImageBase64] = useState<string>("");
  const [results, setResults] = useState<KeywordItem[]>([]);
  const [productContext, setProductContext] = useState<ProductContext | null>(null);

  // Recovery State
  const [hasSavedSession, setHasSavedSession] = useState(false);
  const [restoredProcessed, setRestoredProcessed] = useState<KeywordItem[]>([]);

  // Check for saved session on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        setHasSavedSession(true);
      }
    } catch (e) {
      console.error("Failed to read local storage", e);
    }
  }, []);

  const restoreSession = () => {
    try {
      const saved = localStorage.getItem(SESSION_KEY);
      if (!saved) return;
      const data = JSON.parse(saved);
      
      // Restore state
      setRawKeywords(data.rawKeywords || []);
      setImageBase64(data.imageBase64 || "");
      // Note: We cannot restore the File object itself easily from LS, 
      // but we have the base64 which is what matters for the API.
      // We'll create a dummy file object if needed or just rely on base64.
      const dummyFile = new File([""], "restored_image.jpg", { type: "image/jpeg" });
      setImageFile(dummyFile);
      
      setRestoredProcessed(data.processedKeywords || []);
      
      if (data.productContext) {
        setProductContext(data.productContext);
      }

      setStep(AppStep.ANALYSIS);
      setHasSavedSession(false); // Hide banner once restored
    } catch (e) {
      console.error("Failed to restore session", e);
      alert("Could not restore session due to data corruption.");
      clearSession();
    }
  };

  const clearSession = () => {
    localStorage.removeItem(SESSION_KEY);
    setHasSavedSession(false);
    setRestoredProcessed([]);
  };

  const handleFilesReady = (keywords: string[], imgFile: File, base64: string) => {
    setRawKeywords(keywords);
    setImageFile(imgFile);
    setImageBase64(base64);
    setRestoredProcessed([]); // New upload, no restored items
    setStep(AppStep.ANALYSIS);
  };

  const handleAnalysisComplete = (processedKeywords: KeywordItem[], ctx: ProductContext) => {
    setResults(processedKeywords);
    setProductContext(ctx);
    setStep(AppStep.REVIEW);
    // Optional: Keep session until they export in the review step? 
    // For now we keep it so they can refresh Review page safely if we implemented persistence there too.
  };

  const handleFinish = () => {
      clearSession();
      setStep(AppStep.UPLOAD);
      setResults([]);
      setProductContext(null);
      setRawKeywords([]);
      setImageBase64("");
      setImageFile(null);
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Navbar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2 cursor-pointer" onClick={() => setStep(AppStep.UPLOAD)}>
            <div className="bg-indigo-600 p-2 rounded-lg">
              <BrainCircuit className="text-white w-6 h-6" />
            </div>
            <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-violet-600">
              KeywordLens AI
            </span>
          </div>
          <div className="flex items-center gap-4">
             {hasSavedSession && step === AppStep.UPLOAD && (
                 <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full animate-pulse">
                     <span className="text-xs font-bold text-amber-700">Unfinished session found</span>
                     <button 
                        onClick={restoreSession}
                        className="text-xs bg-amber-500 hover:bg-amber-600 text-white px-2 py-1 rounded transition flex items-center gap-1"
                     >
                        <RotateCcw size={10} /> Resume
                     </button>
                     <button 
                        onClick={clearSession}
                        className="text-xs text-slate-400 hover:text-red-500 p-1"
                        title="Discard"
                     >
                        <Trash2 size={12} />
                     </button>
                 </div>
             )}
             <div className="text-sm text-slate-500 font-medium">
                {step === AppStep.UPLOAD && "Step 1: Setup"}
                {step === AppStep.ANALYSIS && "Step 2: AI Processing"}
                {step === AppStep.REVIEW && "Step 3: Review & Export"}
             </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
        {step === AppStep.UPLOAD && (
          <div className="flex flex-col items-center justify-center min-h-[80vh]">
            <div className="mb-8 text-center max-w-2xl">
              <h1 className="text-4xl font-extrabold text-slate-900 mb-4">Intelligent Keyword Screening</h1>
              <p className="text-lg text-slate-600">
                Upload your product image and Excel keyword list. We'll use multi-modal AI to 
                filter thousands of keywords in minutes, keeping only the most relevant ones.
              </p>
            </div>
            <FileUpload onFilesReady={handleFilesReady} />
          </div>
        )}

        {step === AppStep.ANALYSIS && imageFile && (
          <ProcessingDashboard 
            initialKeywords={rawKeywords}
            initialProcessed={restoredProcessed}
            productImageBase64={imageBase64}
            imageFile={imageFile}
            onAnalysisComplete={handleAnalysisComplete}
          />
        )}

        {step === AppStep.REVIEW && productContext && (
          <ReviewInterface 
            initialKeywords={results}
            productContext={productContext}
          />
        )}
      </main>
    </div>
  );
};

export default App;