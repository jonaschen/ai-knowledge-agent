import os
import time
import subprocess
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ManagerAgent:
    """
    The Autopilot Daemon (Scrum Master).
    Monitors system health, facilitates sprints, and audits team compliance.
    """
    def __init__(self):
        self.repo_path = os.getcwd()
        self.history_path = os.path.join(self.repo_path, "studio", "review_history.md")
        self.optimization_attempts = {} 
        self.MAX_OPTIMIZATION_RETRIES = 3

    def _get_file_mtime(self, filepath):
        if os.path.exists(filepath):
            return os.path.getmtime(filepath)
        return 0

    def audit_reviewer_compliance(self, pr_processed_time):
        """
        [Meta-Monitoring] Verifies if Reviewer actually logged the result.
        """
        history_mtime = self._get_file_mtime(self.history_path)
        
        # Allow a small time buffer (e.g., 5 seconds delay is fine)
        if history_mtime < pr_processed_time:
            logging.warning("🚨 COMPLIANCE ALERT: Reviewer Agent failed to update review_history.md!")
            logging.warning("   -> Triggering Self-Repair for Reviewer...")
            
            # Auto-Fix: Call Architect to check Reviewer's logging logic
            subprocess.run([
                sys.executable, "-m", "studio.architect", 
                "Fix studio/review_agent.py: It failed to write to review_history.md after processing a PR. Check permission or logic error."
            ])
            return False
        
        logging.info("✅ Process Audit Passed: Review history updated.")
        return True

    def autopilot_loop(self):
        logging.info("🤖 Manager Agent (Scrum Master & Auditor) Started.")
        
        while True:
            try:
                # 1. Daily Standup: Monitor PRs
                logging.info("👀 Checking for open PRs (Standup)...")
                
                # Mark time before running reviewer
                start_time = time.time()
                
                result = subprocess.run([sys.executable, "-m", "studio.review_agent"], capture_output=True, text=True)
                
                # If Reviewer did some work (output contains specific keywords)
                if "Processing PR" in result.stderr or "Processing PR" in result.stdout:
                    # 2. Run Audit immediately
                    self.audit_reviewer_compliance(start_time)

                # 3. Health Check
                # healthy = self.run_health_check() ... (省略)

                logging.info("💤 Sleeping for 60 seconds...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                print("\n🛑 Autopilot stopped by user.")
                break
            except Exception as e:
                logging.error(f"Manager Loop Error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    manager = ManagerAgent()
    manager.autopilot_loop()
