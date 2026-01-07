
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
        self.excluded_queue = [] # List of dicts
        
        # State
        self.is_processing = False
        self.current_manual_index = 0
        self.status_message = "Idle"
        self.total_keywords = 0
        self.processed_count = 0
        self.progress = 0 # 0-100 percentage
        
        # Browser Control
        self.searcher: Optional[AmazonSearcher] = None
        
        # Config
        self.MANUAL_THRESHOLD = 0.6
        self.AUTO_THRESHOLD = 0.45
        
        # Lock
        self.lock = threading.Lock()
        
        # Data Storage
        self.original_df = None
        self.keyword_col_name = None

    def start_analysis(self, keywords: List[str], product_description: str):
        """Start the analysis process: Scoring -> Split queues"""
        self.is_processing = True
        self.status_message = "AI Scoring in progress..."
        self.total_keywords = len(keywords)
        self.processed_count = 0
        self.progress = 0
        
        # Clear queues immediately to prevent UI showing old data
        with self.lock:
            self.manual_queue = []
            self.auto_queue = []
            self.excluded_queue = []
        
        # Run in separate thread to not block API
        threading.Thread(target=self._run_scoring_and_split, args=(keywords, product_description)).start()

    def _run_scoring_and_split(self, keywords: List[str], product_description: str):
        """Step 1: AI Scoring & Splitting"""
        try:
            # 1. Scoring
            def progress_cb(percent, msg):
                self.progress = percent
                self.status_message = msg
                
            scored_results = score_keywords(keywords, product_description, progress_callback=progress_cb)
            
            with self.lock:
                self.manual_queue = []
                self.auto_queue = []
                self.excluded_queue = []
                
                for item in scored_results:
                    # Item keys: keyword, score, reason (from zhipu), status
                    
                    if item['score'] > self.MANUAL_THRESHOLD:
                        item['status'] = 'pending'
                        self.manual_queue.append(item)
                    elif item['score'] >= self.AUTO_THRESHOLD:
                         # Auto-approve? or just separate queue?
                         # For now, put in auto queue.
                        item['status'] = 'AUTO'
                        self.auto_queue.append(item)
                        # Maybe mark as kept automatically if it's "Auto"?
                        # item['status'] = 'kept' 
                    else:
                        item['status'] = 'deleted'
                        self.excluded_queue.append(item)
                        # Mark as deleted automatically
                        # item['status'] = 'EXCLUDED'
                
                self.processed_count = len(keywords) # Phase 1 done
                self.progress = 100
                self.status_message = f"Scoring Complete. Manual: {len(self.manual_queue)}, Auto: {len(self.auto_queue)}, Excl: {len(self.excluded_queue)}"
                
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
        try:
            self.status_message = "Opening Browser (Chrome)..."
            
            if not self.searcher:
                # headless=False for manual review
                self.searcher = AmazonSearcher(headless=False, debug=True)
            
            # Always ensure driver is running (creates it if None/closed)
            self.searcher._ensure_driver()
            
            # Verify connectivity
            if self.searcher.driver:
                 _ = self.searcher.driver.title

            self.status_message = "Browser Ready. Waiting for manual review."
            
        except Exception as e:
            self.status_message = f"Browser Init Failed: {str(e)}"
            print(f"Browser Init Error: {e}")
            self.searcher = None

    def get_status(self):
        """Return current status for frontend polling"""
        with self.lock:
            return {
                "status": self.status_message,
                "progress": self.progress,
                "manual_count": len(self.manual_queue),
                "auto_count": len(self.auto_queue),
                "excluded_count": len(self.excluded_queue),
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
            # Sort pending first
            return sorted(self.manual_queue, key=lambda x: 0 if x['status'] == 'pending' else 1)

    def get_all_keywords_list(self):
        """Get ALL keywords for the unified list"""
        with self.lock:
            # Combine all for display
            all_kws = self.manual_queue + self.auto_queue + self.excluded_queue
            # Maybe sort by score?
            return sorted(all_kws, key=lambda x: x['score'] or 0, reverse=True)

    def move_all_to_manual(self):
        """Deprecated: Use configure_manual_review instead"""
        return self.configure_manual_review(True, True, True)

    def configure_manual_review(self, include_manual: bool, include_auto: bool, include_excluded: bool):
        """
        Re-distribute items into manual or auto queues based on user selection.
        Items originally in 'Manual' (>0.6) -> if include_manual: Review, else: Kept
        Items originally in 'Auto' (0.45-0.6) -> if include_auto: Review, else: Kept
        Items originally in 'Excluded' (<0.45) -> if include_excluded: Review, else: Deleted
        """
        with self.lock:
            # 1. Collect all items
            all_items = self.manual_queue + self.auto_queue + self.excluded_queue
            
            # 2. Clear queues
            self.manual_queue = []
            self.auto_queue = []
            self.excluded_queue = []
            
            # 3. Re-distribute
            for item in all_items:
                score = item.get('score', 0)
                
                # Determine original category
                if score > self.MANUAL_THRESHOLD:
                    # Original: Manual
                    if include_manual:
                        item['status'] = 'pending'
                        self.manual_queue.append(item)
                    else:
                        item['status'] = 'kept' # Auto behavior for high score
                        self.auto_queue.append(item)
                        
                elif score >= self.AUTO_THRESHOLD:
                    # Original: Auto
                    if include_auto:
                        item['status'] = 'pending'
                        self.manual_queue.append(item)
                    else:
                        item['status'] = 'AUTO' # Auto behavior for mid score
                        self.auto_queue.append(item)
                        
                else:
                    # Original: Excluded
                    if include_excluded:
                        item['status'] = 'pending'
                        self.manual_queue.append(item)
                    else:
                        item['status'] = 'deleted' # Auto behavior for low score
                        self.excluded_queue.append(item)
            
            # 4. Reset progress/counters
            self.current_manual_index = 0
            self.status_message = f"Queues Configured. Manual Review: {len(self.manual_queue)} items."
            
            # 5. Initialize browser if needed
            if len(self.manual_queue) > 0:
                self.open_browser()
            
            return {"count": len(self.manual_queue)}

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
            elif action == "undecided":
                item['status'] = 'undecided'
            
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
        """Internal: Use searcher to go to page with auto-recovery"""
        def _nav_task():
            # Try up to 2 times (1st attempt, if fail -> restart browser -> 2nd attempt)
            for attempt in range(2):
                try:
                    # Ensure browser exists and is healthy
                    if not self.searcher:
                        self.open_browser()
                    
                    # Double check driver validity by probing simple property
                    try:
                        if self.searcher and self.searcher.driver:
                            # Just accessing a property to check if session is alive
                            _ = self.searcher.driver.window_handles
                    except Exception:
                        # If probe fails, force reopen
                        print("Browser disconnected, restarting...")
                        self.searcher = None
                        self.open_browser()

                    if self.searcher and self.searcher.driver:
                        from urllib.parse import quote
                        url = f"https://www.amazon.com/s?k={quote(keyword)}"
                        self.searcher.driver.get(url)
                        return # Success

                except Exception as e:
                    print(f"Browser Nav Error (Attempt {attempt+1}): {e}")
                    # If this was first attempt, force restart next time
                    if attempt == 0:
                        self.searcher = None
                        # Loop continues to attempt 2
                    else:
                        self.status_message = f"Browser Error: {str(e)}"

        threading.Thread(target=_nav_task).start()

    def shutdown(self):
        if self.searcher:
            self.searcher.close()

    def set_data(self, df: pd.DataFrame, keyword_col: str):
        """Store the original dataframe for export"""
        self.original_df = df
        self.keyword_col_name = keyword_col

    def generate_export_excel(self) -> str:
        """
        Generate Excel file with original data + Score/Status columns inserted
        Returns path to temp file
        """
        with self.lock:
            # Defensive check for attributes (in case of hot reload issues or bad init)
            if not hasattr(self, 'original_df'): self.original_df = None
            if not hasattr(self, 'keyword_col_name'): self.keyword_col_name = None

            if self.original_df is None or self.keyword_col_name is None:
                raise ValueError("No data loaded. Please upload Excel file first.")
                
            # Create a copy to avoid mutating original state
            df = self.original_df.copy()
            
            # Map results to a dictionary for fast lookup
            # Combine all queues
            all_results = self.manual_queue + self.auto_queue + self.excluded_queue
            
            # Create mapping: keyword -> {score, status}
            # Note: This implies original keywords must be unique or we map to first occurrence.
            # If original had duplicates, this simple map might be ambiguous, but acceptable for now.
            result_map = {item['keyword']: item for item in all_results}
            
            scores = []
            statuses = []
            
            for val in df[self.keyword_col_name]:
                val_str = str(val)
                if val_str in result_map:
                    scores.append(result_map[val_str]['score'])
                    statuses.append(result_map[val_str]['status'])
                else:
                    scores.append(None)
                    statuses.append('unprocessed')
            
            # Insert Columns
            target_col_idx = df.columns.get_loc(self.keyword_col_name)
            
            # Helper to safely insert
            def safe_insert(col_name, data):
                if col_name in df.columns:
                    # Drop existing if we want to overwrite, or rename new one?
                    # Let's overwrite
                    del df[col_name]
                    # Recalculate index as dropping might shift it (though target_col_idx is unlikely to change if it's to the left, but let's be safe)
                    # Actually valid approach: just assign
                    df[col_name] = data
                    # But we want specific position.
                    # Simplified: If exists, drop it first.
                
                # Re-calculate index just in case
                curr_idx = df.columns.get_loc(self.keyword_col_name)
                df.insert(curr_idx + 1, col_name, data)

            # Insert Status first (so it pushes right), then Score (so it ends up: Keyword | Score | Status)
            # Note: insert at idx+1 pushes existing idx+1 to idx+2.
            # So if we want [Key, Score, Status], we insert Status at Key+1 -> [Key, Status]
            # Then insert Score at Key+1 -> [Key, Score, Status]
            
            # Check and drop first to avoid "already exists" error
            if 'Status' in df.columns: del df['Status']
            if 'Score' in df.columns: del df['Score']

            # Re-get index after deletions
            base_idx = df.columns.get_loc(self.keyword_col_name)
            
            df.insert(base_idx + 1, 'Status', statuses)
            df.insert(base_idx + 1, 'Score', scores)
            
            # Save to temp file
            # Use absolute path to temp dir or current working dir?
            # Ensure unique name
            filename = f"export_{int(time.time())}_{id(self)}.xlsx"
            filepath = os.path.abspath(os.path.join(os.getcwd(), filename))
            
            try:
                df.to_excel(filepath, index=False)
            except PermissionError:
                # Fallback name if somehow locked
                filename = f"export_{int(time.time())}_fallback.xlsx"
                filepath = os.path.abspath(os.path.join(os.getcwd(), filename))
                df.to_excel(filepath, index=False)
                
            return filepath

# Global instance
engine = WorkflowEngine()
