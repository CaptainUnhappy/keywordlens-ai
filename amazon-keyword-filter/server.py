
import uvicorn
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
import sys
import os
import pandas as pd
import io

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

from scripts.workflow_engine import engine

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow React frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    keywords: List[str]
    product_description: str

class ActionRequest(BaseModel):
    action: str # "keep", "delete"
    index: int

@app.get("/")
def read_root():
    return {"message": "KeywordLens AI Backend is running"}

@app.post("/api/analyze")
def start_analysis(request: AnalyzeRequest):
    """Start the scoring and split process"""
    engine.start_analysis(request.keywords, request.product_description)
    return {"status": "started"}

@app.post("/api/upload_excel")
async def upload_excel(file: UploadFile = File(...)):
    """Parse Excel and return keywords"""
    contents = await file.read()
    try:
        df = pd.read_excel(io.BytesIO(contents))
        # Try to find keyword column
        possible_cols = ['关键词', 'Keyword', 'Search Term', 'keyword']
        found_col = None
        for col in possible_cols:
            if col in df.columns:
                found_col = col
                break
        
        if not found_col:
            # Use first column
            if not df.empty:
                found_col = df.columns[0]
            else:
                 raise HTTPException(status_code=400, detail="Empty Excel")
        
        # Store in engine
        engine.set_data(df, found_col)
                 
        keywords = df[found_col].dropna().astype(str).tolist()
        return {"keywords": keywords, "count": len(keywords)}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

from fastapi.responses import FileResponse

@app.get("/api/export")
def export_results():
    """Generate and return the result Excel"""
    try:
        path = engine.generate_export_excel()
        return FileResponse(path, filename="keyword_analysis_result.xlsx")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/status")
def get_status():
    """Polling endpoint for UI"""
    return engine.get_status()

@app.get("/api/manual_queue")
def get_manual_queue():
    """Get list for review table"""
    return engine.get_manual_list()

@app.post("/api/action")
def perform_action(req: ActionRequest):
    """Keep/Delete action"""
    res = engine.handle_manual_action(req.action, req.index)
    return res

@app.post("/api/navigate")
def navigate_to(index: int = Body(..., embed=True)):
    """Force browser to go to this index"""
    res = engine.manual_navigate(index)
    return res

@app.post("/api/shutdown")
def shutdown():
    engine.shutdown()
    return {"status": "shutting down"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
