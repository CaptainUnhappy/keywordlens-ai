import React, { useState } from 'react';
import { Upload, FileSpreadsheet, ImageIcon, X, CheckCircle, AlertCircle } from 'lucide-react';
import * as XLSX from 'xlsx';
import { readFileAsBase64, readFileAsDataURL } from '../utils';

interface FileUploadProps {
  onFilesReady: (excelData: string[], imageFile: File, imageData: string) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onFilesReady }) => {
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const processFiles = async (files: FileList | File[]) => {
    setError(null);
    let hasValidFile = false;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      
      // Image Check
      if (file.type.startsWith('image/')) {
        const preview = await readFileAsDataURL(file);
        setImagePreview(preview);
        setImageFile(file);
        hasValidFile = true;
      } 
      // Excel/CSV Check
      else if (
        file.name.endsWith('.xlsx') || 
        file.name.endsWith('.xls') || 
        file.name.endsWith('.csv') ||
        file.type.includes('sheet') ||
        file.type.includes('csv') || 
        file.type.includes('excel')
      ) {
        setExcelFile(file);
        
        // Parse immediately
        const reader = new FileReader();
        reader.onload = (evt) => {
            try {
                const bstr = evt.target?.result;
                const wb = XLSX.read(bstr, { type: 'binary' });
                const wsname = wb.SheetNames[0];
                const ws = wb.Sheets[wsname];
                
                // Read as array of arrays (Rows)
                const rows = XLSX.utils.sheet_to_json(ws, { header: 1 }) as any[][];
                
                if (!rows || rows.length === 0) {
                    setError("Excel file appears empty.");
                    return;
                }

                // Smart Column Detection
                let targetColIndex = 0; // Default to first column (Index 0)
                const headerRow = rows[0];

                // Try to find a header that looks like "Keyword"
                if (Array.isArray(headerRow)) {
                    const foundIndex = headerRow.findIndex((cell: any) => 
                        typeof cell === 'string' && 
                        (cell.toLowerCase().includes('keyword') || 
                         cell.includes('关键词') || 
                         cell.toLowerCase().includes('query') ||
                         cell.toLowerCase().includes('term'))
                    );
                    if (foundIndex !== -1) {
                        targetColIndex = foundIndex;
                    }
                }

                // Extract data only from the target column, skipping the header row
                const extractedKeywords = rows
                    .slice(1) // Skip header
                    .map(row => row[targetColIndex]) // Get specific column
                    .filter(cell => typeof cell === 'string' && cell.trim().length > 0) // Ensure it's text
                    .map(cell => cell.trim()); // Trim whitespace

                // Deduplicate
                const uniqueKeywords = Array.from(new Set(extractedKeywords));

                if (uniqueKeywords.length === 0) {
                     setError("No valid keywords found in the selected column.");
                     setKeywords([]);
                } else {
                     setKeywords(uniqueKeywords);
                }

            } catch(e) {
                console.error(e);
                setError("Could not parse Excel file. Please ensure it is a valid format.");
            }
        };
        reader.readAsBinaryString(file);
        hasValidFile = true;
      }
    }

    if (!hasValidFile && files.length > 0) {
        setError("Unsupported file format. Please upload an Image (JPG/PNG) or Excel file.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(e.target.files);
    }
    // Allow re-selecting same file
    e.target.value = '';
  };

  const onDragOver = (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(true);
  };
  
  const onDragLeave = (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          processFiles(e.dataTransfer.files);
      }
  };

  const handleStart = async () => {
    if (imageFile && keywords.length > 0) {
      setLoading(true);
      const base64Data = await readFileAsBase64(imageFile);
      onFilesReady(keywords, imageFile, base64Data);
    }
  };

  const removeImage = (e: React.MouseEvent) => {
      e.preventDefault(); e.stopPropagation();
      setImageFile(null); setImagePreview(null);
  };

  const removeExcel = (e: React.MouseEvent) => {
      e.preventDefault(); e.stopPropagation();
      setExcelFile(null); setKeywords([]);
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-6">
        <div 
          className={`relative group bg-white rounded-3xl shadow-xl border-2 border-dashed transition-all duration-300 min-h-[400px] flex flex-col items-center justify-center overflow-hidden
            ${isDragging ? 'border-indigo-500 bg-indigo-50 scale-[1.02]' : 'border-slate-300 hover:border-indigo-300'}
          `}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
            <input 
              type="file" 
              multiple 
              accept="image/*,.xlsx,.xls,.csv" 
              onChange={handleFileChange} 
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10" 
              title="Click to select files"
            />

            {/* Content Layer (Visuals) */}
            <div className="z-20 p-8 w-full max-w-2xl flex flex-col items-center pointer-events-none">
                 {/* Icons Decoration */}
                 <div className="flex gap-4 mb-6 transition-transform duration-300 group-hover:scale-110">
                     <div className={`p-4 rounded-2xl transition-colors duration-500 ${imageFile ? 'bg-green-100 text-green-600' : 'bg-indigo-50 text-indigo-500'}`}>
                         {imageFile ? <CheckCircle size={32} /> : <ImageIcon size={32} />}
                     </div>
                     <div className={`p-4 rounded-2xl transition-colors duration-500 ${excelFile ? 'bg-green-100 text-green-600' : 'bg-emerald-50 text-emerald-500'}`}>
                         {excelFile ? <CheckCircle size={32} /> : <FileSpreadsheet size={32} />}
                     </div>
                 </div>

                 <h2 className="text-3xl font-bold text-slate-800 mb-3 text-center">
                    {imageFile && excelFile ? "Ready to Launch!" : "Upload Project Files"}
                 </h2>
                 
                 <p className="text-slate-500 text-center mb-8 max-w-md text-lg">
                    {!imageFile && !excelFile && "Drag & Drop your Product Image and Excel list here. You can upload them together or one by one."}
                    {imageFile && !excelFile && "Great! Now just drop your Excel keyword list."}
                    {!imageFile && excelFile && "Perfect! Now drop the Product Image."}
                    {imageFile && excelFile && "All files look good. Click below to start."}
                 </p>

                 {/* File Cards */}
                 <div className="flex flex-wrap gap-4 w-full justify-center pointer-events-auto">
                     {/* Image Card */}
                     <div className={`flex items-center gap-3 p-3 rounded-xl border w-64 transition-all ${imageFile ? 'bg-white border-indigo-200 shadow-md' : 'bg-slate-50 border-slate-200 opacity-60'}`}>
                         {imagePreview ? (
                             <img src={imagePreview} className="w-10 h-10 rounded-lg object-cover bg-slate-200 border border-slate-100" alt="preview" />
                         ) : (
                             <div className="w-10 h-10 rounded-lg bg-slate-200 flex items-center justify-center"><ImageIcon size={16} className="text-slate-400"/></div>
                         )}
                         <div className="flex-1 overflow-hidden">
                             <p className="text-sm font-bold text-slate-700 truncate">{imageFile ? imageFile.name : "Missing Image"}</p>
                             <p className="text-[10px] text-slate-500 uppercase font-bold">{imageFile ? "Attached" : "Required"}</p>
                         </div>
                         {imageFile && <button onClick={removeImage} className="p-1 hover:bg-red-50 text-slate-400 hover:text-red-500 rounded transition"><X size={16}/></button>}
                     </div>

                     {/* Excel Card */}
                     <div className={`flex items-center gap-3 p-3 rounded-xl border w-64 transition-all ${excelFile ? 'bg-white border-green-200 shadow-md' : 'bg-slate-50 border-slate-200 opacity-60'}`}>
                         <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${excelFile ? 'bg-green-100 text-green-600' : 'bg-slate-200 text-slate-400'}`}>
                             <FileSpreadsheet size={20} />
                         </div>
                         <div className="flex-1 overflow-hidden">
                             <p className="text-sm font-bold text-slate-700 truncate">{excelFile ? excelFile.name : "Missing Excel"}</p>
                             <p className="text-[10px] text-slate-500 uppercase font-bold">{keywords.length > 0 ? `${keywords.length} Keywords` : "Required"}</p>
                         </div>
                         {excelFile && <button onClick={removeExcel} className="p-1 hover:bg-red-50 text-slate-400 hover:text-red-500 rounded transition"><X size={16}/></button>}
                     </div>
                 </div>

                 {error && (
                     <div className="mt-6 flex items-center gap-2 text-red-600 bg-red-50 px-4 py-2 rounded-lg text-sm font-medium animate-pulse border border-red-100">
                         <AlertCircle size={16} /> {error}
                     </div>
                 )}
            </div>
        </div>

        <div className="mt-8 flex justify-center">
            <button
                onClick={handleStart}
                disabled={!imageFile || keywords.length === 0 || loading}
                className="group relative px-8 py-4 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-2xl font-bold text-lg shadow-xl shadow-indigo-200 hover:shadow-2xl hover:shadow-indigo-300 transition-all transform hover:-translate-y-1 overflow-hidden"
            >
                <div className="relative z-10 flex items-center gap-3">
                   {loading ? (
                       <>Analyzing...</>
                   ) : (
                       <>Start Analysis <CheckCircle className="group-hover:translate-x-1 transition-transform" size={20}/></>
                   )}
                </div>
            </button>
        </div>
    </div>
  );
};