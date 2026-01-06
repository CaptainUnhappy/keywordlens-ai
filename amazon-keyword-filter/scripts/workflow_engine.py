
import time
import threading
import queue
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
import os

# Import modules
from search_amazon import AmazonSearcher
try:
    from zhipu_scoring import score_keywords
except ImportError:
    # If run from root, adjust path
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))
    from scripts.zhipu_scoring import score_keywords

class WorkflowEngine:
    def __init__(self):
        # Queues
        self.manual_queue = [] # List of dicts: {keyword, score, status}
        self.auto_queue = []   # List of dicts
        
        # State
        self.is_processing = False
        self.current_manual_index = 0
        self.status_message = "Idle"
        self.total_keywords = 0
        self.processed_count = 0
        
        # Browser Control
        self.searcher: Optional[AmazonSearcher] = None
        
        # Config
        self.MANUAL_THRESHOLD = 0.6
        
        # Lock
        self.lock = threading.Lock()

    def start_analysis(self, keywords: List[str], product_description: str):
        """Start the analysis process: Scoring -> Split queues"""
        self.is_processing = True
        self.status_message = "AI Scoring in progress..."
        self.total_keywords = len(keywords)
        self.processed_count = 0
        
        # Run in separate thread to not block API
        threading.Thread(target=self._run_scoring_and_split, args=(keywords, product_description)).start()

    def _run_scoring_and_split(self, keywords: List[str], product_description: str):
        """Step 1: AI Scoring & Splitting"""
        try:
            # 1. Scoring
            scored_results = score_keywords(keywords, product_description)
            
            with self.lock:
                self.manual_queue = []
                self.auto_queue = []
                
                for item in scored_results:
                    item['status'] = 'pending' # pending, kept, deleted
                    if item['score'] > self.MANUAL_THRESHOLD:
                        self.manual_queue.append(item)
                    else:
                        self.auto_queue.append(item)
                
                self.processed_count = len(keywords) # Phase 1 done
                self.status_message = f"Scoring Complete. Manual: {len(self.manual_queue)}, Auto: {len(self.auto_queue)}"
                
            # 2. Trigger Auto workflow (Optional: for now just mark them)
            # self._start_auto_crawler() 
            
            # 3. Ready for manual review
            # Initialize browser if manual queue exists
            if self.manual_queue:
                self.open_browser()
                # Automatically load first item? Maybe wait for user action
                
        except Exception as e:
            self.status_message = f"Error during scoring: {str(e)}"
            print(f"Workflow Error: {e}")
        finally:
            # self.is_processing = False # Keep processing true until everything is done?
            pass

    def open_browser(self):
        """Initialize browser for manual review"""
        if not self.searcher:
            try:
                self.status_message = "Opening Browser (Chrome)..."
                # headless=False for manual review
                self.searcher = AmazonSearcher(headless=False, debug=True)
                self.status_message = "Browser Ready. Waiting for manual review."
            except Exception as e:
                self.status_message = f"Browser Init Failed: {str(e)}"
                print(f"Browser Init Error: {e}")
        else:
             # If it exists, check if alive
             try:
                 if self.searcher.driver:
                     self.searcher.driver.title # Probe
             except:
                 self.searcher = None
                 self.open_browser()

    def get_status(self):
        """Return current status for frontend polling"""
        with self.lock:
            return {
                "status": self.status_message,
                "manual_count": len(self.manual_queue),
                "auto_count": len(self.auto_queue),
                "manual_pending": len([x for x in self.manual_queue if x['status'] == 'pending']),
                "current_manual_index": self.current_manual_index,
                "current_keyword": self._get_current_manual_keyword()
            }
            
    def _get_current_manual_keyword(self):
        if 0 <= self.current_manual_index < len(self.manual_queue):
            return self.manual_queue[self.current_manual_index]
        return None

    def get_manual_list(self):
        """Get the full list of manual keywords"""
        with self.lock:
            return self.manual_queue

    def handle_manual_action(self, action: str, index: int):
        """Handle Keep/Delete action from frontend"""
        with self.lock:
            if index < 0 or index >= len(self.manual_queue):
                return {"error": "Invalid index"}
                
            item = self.manual_queue[index]
            
            if action == "keep":
                item['status'] = 'kept'
            elif action == "delete":
                item['status'] = 'deleted'
            
            # Move to next
            next_index = index + 1
            self.current_manual_index = next_index
            
            # Trigger Browser Navigation for NEXT item
            if next_index < len(self.manual_queue):
                next_item = self.manual_queue[next_index]
                self._navigate_browser(next_item['keyword'])
            else:
                self.status_message = "Manual Review Complete!"
                # Close browser?
                # if self.searcher: self.searcher.close()
            
            return {"success": True, "next_index": next_index}

    def manual_navigate(self, index: int):
        """Force browser navigation to specific index"""
        with self.lock:
            if 0 <= index < len(self.manual_queue):
                self.current_manual_index = index
                item = self.manual_queue[index]
                self._navigate_browser(item['keyword'])
                return {"success": True}
        return {"error": "Index out of bounds"}

    def _navigate_browser(self, keyword: str):
        """Internal: Use searcher to go to page"""
        if not self.searcher:
            self.open_browser()
            
        def _nav_task():
            if self.searcher:
                try:
                    # Use existing search method but just load page is enough?
                    # Using search() fetches images, but for review we just want to SEE the page
                    # searcher.search(keyword) might be too heavy if it scrapes images
                    # Let's just use driver.get directly
                    from urllib.parse import quote
                    url = f"https://www.amazon.com/s?k={quote(keyword)}"
                    if self.searcher.driver:
                        self.searcher.driver.get(url)
                except Exception as e:
                    print(f"Browser Nav Error: {e}")

        threading.Thread(target=_nav_task).start()

    def shutdown(self):
        if self.searcher:
            self.searcher.close()

# Global instance
engine = WorkflowEngine()
