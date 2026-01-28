import os
import time
import subprocess
import logging
import sys
import argparse
from dotenv import load_dotenv
from product import main as product_main

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
        self.repo_path = os.getcwd()
        self.optimization_attempts = {} # Track attempts per component {component: count}
        self.MAX_OPTIMIZATION_RETRIES = 3 # Circuit Breaker limit
        self.last_health_check_time = 0.0

    def run_health_check(self, last_check_time: float = 0.0) -> float:
        """Runs the e2e health check if an hour has passed or if forced."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--run-now', action='store_true', help='Force health check to run immediately.')
        # Use parse_known_args to avoid conflicts with other potential args
        args, _ = parser.parse_known_args()

        now = time.time()
        one_hour_in_seconds = 3600

        if args.run_now or (now - last_check_time > one_hour_in_seconds):
            print("MANAGER: Running system health check...")
            try:
                # Assuming product.main has a runnable function
                product_main.run_deep_context_reader('AI Agents')
                print("MANAGER: Health check PASSED.")
                return now
            except Exception as e:
                print(f"MANAGER: Health check FAILED: {e}")
                # Future: Log this failure to review_history.md
                return now # Update time to prevent immediate re-run
        return last_check_time


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
                
                # 2. Sprint Review: Health Check
                self.last_health_check_time = self.run_health_check(last_check_time=self.last_health_check_time)
                
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
