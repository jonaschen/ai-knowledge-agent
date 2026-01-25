import subprocess
import git # Assumes GitPython is installed
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReviewAgent:
    """
    Automated QA agent that runs tests on a branch and merges it on success.
    """
    def __init__(self, repo_path: str):
        """
        Initializes the agent with the path to the git repository.
        """
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            logging.error(f"Invalid git repository at path: {repo_path}")
            self.repo = None

    def run_tests(self) -> bool:
        """
        Runs the pytest suite and returns True for success, False for failure.
        """
        if not self.repo:
            logging.error("Cannot run tests, repository not initialized.")
            return False

        logging.info("Running pytest suite...")
        # We use check=False to prevent subprocess from raising an exception on non-zero exit codes.
        result = subprocess.run(['pytest'], capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logging.info("✅ Pytest suite passed.")
            return True
        else:
            logging.error("❌ Pytest suite failed.")
            logging.error(f"STDOUT:\n{result.stdout}")
            logging.error(f"STDERR:\n{result.stderr}")
            # NOTE: In a future iteration, we will log this failure to review_history.md
            return False

    def merge_pr(self, branch_name: str) -> bool:
        """
        Merges the specified branch into the current branch (e.g., main).
        """
        if not self.repo:
            logging.error("Cannot merge, repository not initialized.")
            return False

        try:
            current_branch = self.repo.active_branch
            logging.info(f"Attempting to merge '{branch_name}' into '{current_branch.name}'...")
            self.repo.git.merge(branch_name)
            logging.info(f"✅ Successfully merged '{branch_name}'.")
            return True
        except git.GitCommandError as e:
            logging.error(f"❌ Merge failed: {e}")
            self.repo.git.merge('--abort')
            logging.warning("Merge aborted.")
            return False

    def process_pr(self, branch_name: str) -> bool:
        """
        Orchestrates the full review and merge process for a given branch.
        """
        logging.info(f"Processing PR for branch: '{branch_name}'")

        # For safety, ensure we are on the main branch before merging
        # In a real CI/CD, this would be more robust.
        # self.repo.heads.main.checkout()

        if self.run_tests():
            return self.merge_pr(branch_name)
        else:
            logging.warning(f"Skipping merge for '{branch_name}' due to test failures.")
            return False