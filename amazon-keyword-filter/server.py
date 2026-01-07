
import uvicorn
import logging
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

from contextlib import asynccontextmanager

# Custom Log Filter
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Try to parse from args if available (Uvicorn standard)
        # args: (client_addr, method, full_path, protocol, status_code)
        if record.args and len(record.args) >= 5:
            try:
                path = str(record.args[2])
                status = int(record.args[4])
                
                if status == 200:
                    if path in ["/api/manual_queue", "/api/all_keywords", "/api/status"]:
                        return False
            except (ValueError, IndexError):
                pass
        
        # Fallback to string matching
        message = record.getMessage()
        if "200 OK" in message:
            if "/api/manual_queue" in message: return False
            if "/api/all_keywords" in message: return False
            if "/api/status" in message: return False
            
        return True

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Add filter
    # Force get logger
    logger = logging.getLogger("uvicorn.access")
    
    # Create filter
    f = EndpointFilter()
    logger.addFilter(f)
    
    # Also attach to all handlers to be safe
    for handler in logger.handlers:
        handler.addFilter(f)
        
    yield
    # Shutdown logic (if any) can go here

app = FastAPI(lifespan=lifespan)


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
    product_image: Optional[str] = None

class ActionRequest(BaseModel):
    action: str # "keep", "delete", "undecided"
    index: int

@app.get("/")
def read_root():
    return {"message": "KeywordLens AI Backend is running"}

@app.post("/api/analyze")
def start_analysis(request: AnalyzeRequest):
    """Start the scoring and split process"""
    engine.start_analysis(request.keywords, request.product_description, request.product_image)
    return {"status": "started"}

@app.post("/api/start_verification")
def start_verification():
    """Manually start the image verification (Step 3)"""
    return engine.start_auto_verification()

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

@app.get("/api/all_keywords")
def get_all_keywords():
    """Get all keywords for right sidebar"""
    return engine.get_all_keywords_list()

class ReviewConfig(BaseModel):
    include_manual: bool
    include_auto: bool
    include_excluded: bool

@app.post("/api/configure_review")
def configure_review(config: ReviewConfig):
    """Configure selective manual review"""
    return engine.configure_manual_review(
        config.include_manual,
        config.include_auto,
        config.include_excluded
    )

@app.post("/api/move_all_manual")
def move_all_manual():
    """Deprecated: Use configure_review"""
    return engine.configure_manual_review(True, True, True)

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

@app.post("/api/open_browser")
def open_browser():
    """Manually open the browser"""
    engine.open_browser()
    return {"status": "browser opened"}

@app.post("/api/shutdown")
def shutdown():
    engine.shutdown()
    return {"status": "shutting down"}

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
