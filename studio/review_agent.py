# studio/review_agent.py
import os
import subprocess
import logging
from github import Github

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReviewAgent:
    def __init__(self, repo_path: str, github_client):
        self.repo_path = repo_path
        self.github_client = github_client
        # self.repo = self.github_client.get_repo(repo_name) # Mocked in tests

    def process_open_prs(self, open_prs):
        """
        Processes a list of PRs, runs tests, and merges if they pass.
        """
        if not open_prs:
            logging.info("No open pull requests found.")
            return

        for pr in open_prs:
            local_pr_branch = f"pr-{pr.number}"
            fetch_ref = f"pull/{pr.number}/head:{local_pr_branch}"
            test_result = None

            try:
                try:
                    # Fetch and checkout
                    subprocess.run(['git', 'fetch', 'origin', fetch_ref], check=True, cwd=self.repo_path)
                    subprocess.run(['git', 'checkout', local_pr_branch], check=True, cwd=self.repo_path)

                    # Run tests
                    test_result = subprocess.run(['pytest'], capture_output=True, text=True, cwd=self.repo_path)

                finally:
                    # Always switch back to main and clean up the local branch
                    subprocess.run(['git', 'checkout', 'main'], check=True, cwd=self.repo_path)
                    # Suppress errors if branch doesn't exist (e.g., if checkout failed)
                    subprocess.run(['git', 'branch', '-D', local_pr_branch], check=False, cwd=self.repo_path, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

                # Conditional merge
                if test_result and test_result.returncode == 0:
                    logging.info(f"Tests passed for PR #{pr.number}. Merging.")
                    try:
                        pr.merge()
                        logging.info(f"Successfully merged PR #{pr.number}.")
                    except Exception as e:
                        logging.error(f"Failed to merge PR #{pr.number}: {e}")
                else:
                    logging.warning(f"Tests failed for PR #{pr.number}. Not merging.")
                    if test_result:
                        logging.warning(f"Pytest output:\n{test_result.stdout}\n{test_result.stderr}")

            except subprocess.CalledProcessError as e:
                logging.error(f"A git command failed while processing PR #{pr.number}: {e}")
                logging.error(f"Command: '{e.cmd}'\nStderr: {e.stderr}")
                # Continue to the next PR
            except Exception as e:
                logging.error(f"An unexpected error occurred for PR #{pr.number}: {e}")

