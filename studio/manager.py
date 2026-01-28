from product import main as product_main
from studio import review_agent
import os
import time
import subprocess
import logging
import sys
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_run_artifacts(log_path: str, mp3_path: str) -> tuple[bool, str]:
    """
    Performs a health check on the output artifacts of a product run.

    Args:
        log_path: Path to the output log file.
        mp3_path: Path to the output mp3 file.

    Returns:
        A tuple containing a boolean for health status and a reason string.
    """
    # 1. Check for MP3 file existence
    if not os.path.exists(mp3_path):
        return False, f"Missing output file: {mp3_path}"

    # 2. Check for log file existence
    if not os.path.exists(log_path):
        return False, f"Missing log file: {log_path}"

    # 3. Check log file for errors
    with open(log_path, 'r') as f:
        log_content = f.read()
        # Define sensitive error keywords
        error_keywords = ["ERROR", "FAILURE", "Traceback"]
        if any(keyword in log_content for keyword in error_keywords):
            return False, "Error detected in log file."

    return True, "Artifacts verified successfully."

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
        self.history_path = os.path.join(self.repo_path, "studio", "review_history.md")
        self.last_check_time = 0.0


    def run_health_check(self):
        """Runs the full product pipeline with a default topic."""
        print("--- Running Hourly Health Check ---")
        try:
            # This call must be mockable in tests
            product_main.run(topic='AI Agents')
            print("--- Health Check PASSED ---")
        except Exception as e:
            print(f"--- Health Check FAILED: {e} ---")
            # Future: Log this failure to review_history.md

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

    def autopilot_loop(self, run_once=False):
        """
        The main infinite loop (The Scrum Sprint).
        """
        logging.info("🤖 Manager Agent (Scrum Master) Started.")
        
        while True:
            try:
                # 1. Daily Standup: Monitor PRs (Keep the pipeline moving)
                logging.info("👀 Checking for open PRs (Standup)...")

                # The review_agent script now handles its own logging, including successes.
                # Manager's job is just to trigger it.
                subprocess.run([sys.executable, "-m", "studio.review_agent"], check=False)
                
                # 2. Sprint Review: Health Check
                now = time.time()
                is_time_to_check = (now - self.last_check_time) > 3600
                is_forced_run = '--run-now' in sys.argv

                if is_time_to_check or is_forced_run:
                    self.run_health_check()
                    self.last_check_time = now # Reset timer
                
                logging.info("💤 Sleeping for 60 seconds...")
                time.sleep(60)

            except KeyboardInterrupt:
                print("\n🛑 Autopilot stopped by user.")
                break
            except Exception as e:
                logging.error(f"Manager Loop Error: {e}")
                time.sleep(60)

            if run_once:
                return


def main():
    """
    Main execution loop for the Manager agent.
    """
    try:
        logging.info("Manager starting. Attempting to pull latest codebase...")
        # The check=True flag will raise CalledProcessError on a non-zero exit code.
        subprocess.run(['git', 'pull'], check=True, capture_output=True, text=True)
        logging.info("Codebase is up to date.")
    except subprocess.CalledProcessError as e:
        logging.error(f"FATAL: Failed to pull latest code. A manual intervention may be required. Error: {e.stderr}")
        # Exit to prevent the manager from running on a stale/conflicted codebase.
        sys.exit(1)
    except FileNotFoundError:
        logging.error("FATAL: 'git' command not found. Ensure git is installed and in the system's PATH.")
        sys.exit(1)

    manager = ManagerAgent()
    try:
        manager.autopilot_loop()
    except KeyboardInterrupt:
        print("\n🛑 Autopilot stopped by user.")


if __name__ == "__main__":
    main()
