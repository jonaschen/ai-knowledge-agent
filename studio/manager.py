import os
import time
import subprocess
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ManagerAgent:
    """
    The Autopilot Daemon.
    Monitors the system health and orchestrates the team (Architect, Optimizer, Reviewer).
    """
    def __init__(self):
        self.health_check_interval = 3600 # Run every hour (simulated)
        self.repo_path = os.getcwd()

    def run_health_check(self) -> bool:
        """
        Runs the main product pipeline as a smoke test.
        Returns True if successful, False if failed.
        """
        logging.info("🏥 Running System Health Check (Smoke Test)...")
        try:
            # Run a standard test topic
            result = subprocess.run(
                [sys.executable, "-m", "product.main", "smoke_test_topic"],
                capture_output=True,
                text=True,
                cwd=self.repo_path
            )
            
            if result.returncode == 0:
                logging.info("✅ Health Check Passed.")
                return True
            else:
                logging.error(f"❌ Health Check Failed:\n{result.stderr[-500:]}")
                return False
        except Exception as e:
            logging.error(f"Health check execution error: {e}")
            return False

    def trigger_recovery(self, failure_type="logic"):
        """
        Decides who to call based on failure type.
        """
        if failure_type == "quality":
            # If it runs but produces bad output (detected by Verifier/Analyst score)
            logging.info("📞 Calling Optimizer Agent to refine prompts...")
            # Ideally, we optimize the component that failed. Defaulting to Analyst.
            subprocess.run([sys.executable, "-m", "studio.optimizer", "product/analyst_core.py"])
            
        elif failure_type == "logic":
            # If it crashes -> Call Architect to fix code (currently manual trigger for safety)
            logging.warning("📞 System Crash Detected. Architect intervention recommended.")
            # In full autonomy, we would:
            # subprocess.run([sys.executable, "-m", "studio.architect", "Fix the crash detected in health check..."])

    def autopilot_loop(self):
        """
        The main infinite loop.
        """
        logging.info("🤖 Manager Agent (Autopilot) Started.")
        
        while True:
            try:
                # 1. Monitor PRs (Keep the pipeline moving)
                # This ensures any pending fixes from Jules/Optimizer are merged
                logging.info("👀 Checking for open PRs...")
                subprocess.run([sys.executable, "-m", "studio.review_agent"])
                
                # 2. Health Check (Simulated Frequency - currently simplified)
                # Uncomment below to enable active probing
                # healthy = self.run_health_check()
                # if not healthy:
                #     self.trigger_recovery("logic")
                
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




