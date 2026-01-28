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
    The Autopilot Daemon (Scrum Master).
    Monitors the system health, facilitates sprints, and orchestrates recovery.
    Includes Circuit Breakers to prevent infinite loops.
    """
    def __init__(self):
        self.health_check_interval = 3600 # Run every hour (simulated)
        self.repo_path = os.getcwd()
        self.optimization_attempts = {} # Track attempts per component {component: count}
        self.MAX_OPTIMIZATION_RETRIES = 3 # Circuit Breaker limit

    def run_health_check(self) -> bool:
        """
        Runs the main product pipeline as a smoke test / golden set test.
        Returns True if successful, False if failed.
        """
        logging.info("🏥 Running System Health Check (Smoke Test)...")
        try:
            # Run a standard test topic
            # In a real scenario, this would run a 'Golden Set' of tests
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
        target_component = "product/analyst_core.py" # Example target based on failure analysis
        
        if failure_type == "quality":
            # Circuit Breaker Check
            current_retries = self.optimization_attempts.get(target_component, 0)
            if current_retries >= self.MAX_OPTIMIZATION_RETRIES:
                logging.critical(f"🛑 Circuit Breaker Tripped! {target_component} failed optimization {current_retries} times.")
                logging.critical("Manual intervention required. Stopping Autopilot.")
                return # Stop trying

            # If it runs but produces bad output (detected by Verifier/Analyst score)
            logging.info("📞 Calling Optimizer Agent to refine prompts...")
            
            subprocess.run([sys.executable, "-m", "studio.optimizer", target_component])
            self.optimization_attempts[target_component] = current_retries + 1
            
        elif failure_type == "logic":
            # If it crashes -> Call Architect to fix code (currently manual trigger for safety)
            logging.warning("📞 System Crash Detected. Architect intervention recommended.")
            # In full autonomy, we would:
            # subprocess.run([sys.executable, "-m", "studio.architect", "Fix the crash detected in health check..."])

    def autopilot_loop(self):
        """
        The main infinite loop (The Scrum Sprint).
        """
        logging.info("🤖 Manager Agent (Scrum Master) Started.")
        
        while True:
            try:
                # 1. Daily Standup: Monitor PRs (Keep the pipeline moving)
                # This ensures any pending fixes from Jules/Optimizer are merged
                logging.info("👀 Checking for open PRs (Standup)...")
                subprocess.run([sys.executable, "-m", "studio.review_agent"])
                
                # 2. Sprint Review: Health Check (Simulated Frequency - currently simplified)
                # Uncomment below to enable active probing
                # healthy = self.run_health_check()
                # if not healthy:
                #     self.trigger_recovery("logic") # Or "quality"
                
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
    try:
        manager.autopilot_loop()
    except KeyboardInterrupt:
        print("\n🛑 Autopilot stopped by user.")
