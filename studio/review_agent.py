# studio/review_agent.py
import os
import subprocess
import logging
from github import Github

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReviewAgent:
    def __init__(self, repo_name: str, github_token: str):
        if not repo_name or not github_token:
            raise ValueError("Repo name and GitHub token are required.")
        self.github = Github(github_token)
        self.repo = self.github.get_repo(repo_name)
        logging.info(f"Initialized ReviewAgent for repo: {self.repo.full_name}")

    def process_open_prs(self):
        """
        Fetches open PRs, runs tests, and merges if they pass.
        """
        open_pulls = list(self.repo.get_pulls(state='open'))
        if not open_pulls:
            logging.info("No open pull requests found.")
            return

        for pr in open_pulls:
            logging.info(f"Processing PR #{pr.number}: '{pr.title}'")

            # In a real CI environment, the runner would have already checked out the PR's branch.
            # We assume the current working directory contains the code for the PR.

            result = subprocess.run(['pytest'], capture_output=True, text=True)

            if result.returncode == 0:
                logging.info(f"Tests passed for PR #{pr.number}. Merging.")
                try:
                    pr.merge()
                    logging.info(f"Successfully merged PR #{pr.number}.")
                except Exception as e:
                    logging.error(f"Failed to merge PR #{pr.number}: {e}")
            else:
                logging.warning(f"Tests failed for PR #{pr.number}. The PR will not be merged.")
                logging.warning(f"Pytest output:\n{result.stdout}\n{result.stderr}")

if __name__ == '__main__':
    # Example usage: expects environment variables for configuration
    repo_name = os.getenv("GITHUB_REPOSITORY") # e.g., "MyOrg/DeepContextReader"
    token = os.getenv("GITHUB_TOKEN")

    if not repo_name or not token:
        logging.error("GITHUB_REPOSITORY and GITHUB_TOKEN environment variables must be set.")
    else:
        agent = ReviewAgent(repo_name=repo_name, github_token=token)
        agent.process_open_prs()
