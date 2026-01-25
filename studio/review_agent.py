import os
import subprocess
import logging
import sys
import re
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_command(command: list) -> (int, str, str):
    """Runs a command and returns its exit code, stdout, and stderr."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError as e:
        return 1, "", f"Command not found: {e}"
    except Exception as e:
        return 1, "", f"An unexpected error occurred: {e}"

def get_open_prs():
    """Fetches and sorts open pull requests by creation date (FIFO)."""
    command = ['gh', 'pr', 'list', '--json', 'number,headRefName,createdAt']
    returncode, stdout, stderr = run_command(command)
    if returncode != 0:
        logging.error(f"Failed to get open PRs: {stderr}")
        return []

    try:
        prs = json.loads(stdout)
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from gh command: {stdout}")
        return []

    # Sort PRs by 'createdAt' field in ascending order
    return sorted(prs, key=lambda pr: datetime.fromisoformat(pr['createdAt'].replace("Z", "+00:00")))

class ReviewAgent:
    def run(self):
        """Main processing loop for the review agent."""
        open_prs = get_open_prs()
        if not open_prs:
            logging.info("No open pull requests found.")
            return

        for pr in open_prs:
            pr_number = pr['number']
            # Correct key for branch name from `gh pr list` JSON
            branch_name = pr['headRefName']
            logging.info(f"Processing PR #{pr_number}: '{branch_name}'")

            try:
                # 1. Checkout PR branch
                run_command(['git', 'fetch', 'origin'])
                returncode, _, stderr = run_command(['git', 'checkout', branch_name])
                if returncode != 0:
                    logging.error(f"Failed to checkout branch {branch_name}: {stderr}")
                    continue

                # 2. Run Tests
                logging.info(f"Running pytest for PR #{pr_number}...")
                test_returncode, test_stdout, test_stderr = run_command(['pytest'])

                if test_returncode == 0:
                    logging.info(f"✅ Tests passed for PR #{pr_number}.")
                    self.handle_test_success(branch_name)
                else:
                    logging.warning(f"❌ Tests failed for PR #{pr_number}.")
                    failure_output = test_stdout + "\n" + test_stderr
                    self.handle_test_failure(pr_number, branch_name, failure_output)

            finally:
                # 4. Cleanup: Always switch back to main
                run_command(['git', 'checkout', 'main'])

    def handle_test_success(self, branch_name: str):
        """Handles the git workflow for a successful test run."""
        logging.info(f"Merging branch '{branch_name}' into main.")
        run_command(['git', 'checkout', 'main'])
        run_command(['git', 'merge', '--no-ff', branch_name])
        run_command(['git', 'push', 'origin', 'main'])

    def handle_test_failure(self, pr_number: int, branch_name: str, failure_output: str):
        """Handles the git workflow for a failed test run."""
        # 1. Construct failure message
        today = datetime.now().strftime("%Y-%m-%d")
        root_cause = "Could not determine root cause from output."
        # A more robust regex to find the 'E' line, even with leading whitespace
        error_line_match = re.search(r"^\s*E\s+(.*)$", failure_output, re.MULTILINE)
        if error_line_match:
            root_cause = error_line_match.group(1).strip()

        log_entry = f"""
## [PR #{pr_number}] Test Failure
- **Date**: {today}
- **Root Cause**: {root_cause}
"""
        # 2. Append to review_history.md
        with open('studio/review_history.md', 'a') as f:
            f.write(log_entry)

        # 3. Commit and push the history file
        run_command(['git', 'add', 'studio/review_history.md'])
        commit_message = f"docs: Log test failure for PR #{pr_number}"
        run_command(['git', 'commit', '-m', commit_message])
        run_command(['git', 'push', 'origin', branch_name])

if __name__ == '__main__':
    # This check ensures the agent runs only when the script is executed directly
    agent = ReviewAgent()
    agent.run()