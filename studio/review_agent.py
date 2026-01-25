import os
import subprocess
import logging
import sys
import re
from datetime import datetime
from github import Github
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReviewAgent:
    def __init__(self, repo_path: str, github_client):
        self.repo_path = repo_path
        self.github_client = github_client

    def process_open_prs(self, open_prs):
        """
        Processes a list of PRs, runs tests, merges if pass, COMMENTS if fail.
        """
        if not open_prs:
            logging.info("No open pull requests found.")
            return

        for pr in open_prs:
            logging.info(f"Processing PR #{pr.number}: '{pr.title}'")
            local_pr_branch = f"pr-{pr.number}"
            # 修正: 使用 pull/ID/head 確保抓到的是 PR 的最新 commit
            fetch_ref = f"pull/{pr.number}/head:{local_pr_branch}"

            try:
                try:
                    # 1. Fetch and Checkout
                    logging.info(f"Fetching and checking out PR #{pr.number}...")
                    subprocess.run(['git', 'fetch', 'origin', fetch_ref], check=True, cwd=self.repo_path, capture_output=True)
                    subprocess.run(['git', 'checkout', local_pr_branch], check=True, cwd=self.repo_path, capture_output=True)

                    # 2. Run Tests (使用當前 Python 環境)
                    logging.info(f"Running pytest for PR #{pr.number}...")
                    test_result = subprocess.run(
                        [sys.executable, '-m', 'pytest'], 
                        capture_output=True, 
                        text=True, 
                        cwd=self.repo_path
                    )

                    # 3. Handle Result
                    if test_result.returncode == 0:
                        logging.info(f"✅ Tests passed for PR #{pr.number}.")
                        # Double check if PR is mergeable (not draft)
                        if pr.draft:
                            logging.warning(f"PR #{pr.number} is a Draft. Cannot merge automatically.")
                            # Optional: Comment "Ready for review?"
                        else:
                            logging.info(f"Merging PR #{pr.number}...")
                            pr.merge(merge_method='squash')
                            logging.info(f"🚀 Successfully merged PR #{pr.number}.")
                    
                    else:
                        logging.warning(f"❌ Tests failed for PR #{pr.number}.")
                        
                        # --- Feedback Loop: Analyze and Comment ---
                        error_log = test_result.stdout[-2000:] + "\n" + test_result.stderr[-2000:] # 取最後 2000 字避免太長

                        # Analyze failure
                        analysis = self.analyze_failure(error_log, pr.number)

                        # Write history
                        self.write_history(analysis)

                        # Commit and Push
                        try:
                            logging.info(f"Committing review_history.md to PR #{pr.number}...")
                            # Add the file
                            subprocess.run(['git', 'add', 'studio/review_history.md'], check=True, cwd=self.repo_path, capture_output=True)

                            # Commit
                            commit_msg = f"docs: update review history for PR #{pr.number} failure [skip ci]"
                            subprocess.run(['git', 'commit', '-m', commit_msg], check=True, cwd=self.repo_path, capture_output=True)

                            # Push
                            # Push local_pr_branch to origin pr.head.ref
                            push_ref = f"{local_pr_branch}:{pr.head.ref}"
                            logging.info(f"Pushing to origin {push_ref}...")
                            subprocess.run(['git', 'push', 'origin', push_ref], check=True, cwd=self.repo_path, capture_output=True)

                        except subprocess.CalledProcessError as e:
                            logging.error(f"Failed to commit/push history for PR #{pr.number}: {e}")
                            if e.stderr:
                                logging.error(f"Git stderr: {e.stderr.decode()}")

                        comment_body = (
                            f"## ❌ Automated Review Failed\n\n"
                            f"**ReviewAgent** found issues in component: **{analysis.get('component', 'Unknown')}**\n"
                            f"- **Error Type**: {analysis.get('error_type', 'Unknown')}\n"
                            f"- **Root Cause**: {analysis.get('root_cause', 'Unknown')}\n\n"
                            f"Please check `studio/review_history.md` for details or expand the log below.\n\n"
                            f"<details>\n<summary>Click to see Error Log</summary>\n\n"
                            f"```text\n{error_log}\n```\n"
                            f"\n</details>"
                        )
                        
                        # 檢查是否已經留言過同樣的錯誤 (避免洗版) - 這裡做簡單處理，直接留言
                        logging.info(f"Posting error report to PR #{pr.number}...")
                        pr.create_issue_comment(comment_body)
                        # ---------------------------------------------

                except subprocess.CalledProcessError as e:
                    logging.error(f"Git command failed for PR #{pr.number}: {e}")
                except Exception as e:
                    logging.error(f"An unexpected error occurred: {e}")

            finally:
                # 4. Cleanup: Always switch back to main
                try:
                    subprocess.run(['git', 'checkout', 'main'], check=True, cwd=self.repo_path, capture_output=True)
                    # Optional: Delete the temp branch to keep local clean
                    subprocess.run(['git', 'branch', '-D', local_pr_branch], check=False, cwd=self.repo_path, capture_output=True)
                except Exception as e:
                    logging.warning(f"Cleanup failed: {e}")

    def analyze_failure(self, pytest_output: str, pr_id: int):
        analysis = {'pr_id': pr_id}

        # 1. Extract Component from the failing test file path
        component_match = re.search(r'tests/test_(.*?)\.py', pytest_output)
        if component_match:
            analysis['component'] = component_match.group(1).capitalize()
        else:
            analysis['component'] = 'Unknown'

        # 2. Extract Root Cause from the line starting with 'E'
        root_cause = "Could not determine root cause"
        error_line_match = re.search(r"^E\s+(.*)$", pytest_output, re.MULTILINE)
        if error_line_match:
            root_cause = error_line_match.group(1).strip()

            # Append file context if available
            file_context_match = re.search(r"^(tests/test_.*\.py):\d+: ", pytest_output, re.MULTILINE)
            if file_context_match:
                root_cause += f" in {file_context_match.group(1)}"
        analysis['root_cause'] = root_cause

        # 3. Determine Error Type (currently rule-based)
        error_type = 'Generic Test Failure'
        if 'DID NOT RAISE' in root_cause and 'APITimeout' in root_cause:
            error_type = 'APITimeout Handling Error'
        analysis['error_type'] = error_type

        return analysis

    def write_history(self, analysis: dict):
        today = datetime.now().strftime("%Y-%m-%d")

        # Ensure required keys exist to prevent errors, providing default values
        component = analysis.get('component', 'Unknown Component')
        error_type = analysis.get('error_type', 'Undefined Error')
        root_cause = analysis.get('root_cause', 'No root cause specified.')
        fix_pattern = analysis.get('fix_pattern', 'No fix pattern provided.')
        tags = analysis.get('tags', '#untagged')
        pr_id = analysis.get('pr_id', 'N/A')

        log_entry = f"""
## [PR #{pr_id}] {component} Failure
- **Date**: {today}
- **Error Type**: {error_type}
- **Root Cause**: {root_cause}
- **Fix Pattern**: {fix_pattern}
- **Tags**: {tags}
"""
        # Append to the history file
        history_path = os.path.join(self.repo_path, 'studio', 'review_history.md')

        # Ensure directory exists
        os.makedirs(os.path.dirname(history_path), exist_ok=True)

        with open(history_path, 'a') as f:
            f.write(log_entry)

# --- Entry Point ---
if __name__ == '__main__':
    print("🔍 DEBUG: Starting Review Agent v2.0...")

    is_loaded = load_dotenv()
    cwd = os.getcwd()

    repo_name_str = os.getenv("GITHUB_REPOSITORY")
    token_str = os.getenv("GITHUB_TOKEN")

    if not repo_name_str or not token_str:
        print("❌ ERROR: Missing environment variables!")
        exit(1)

    try:
        print("🚀 DEBUG: Logging into GitHub...")
        gh_client = Github(token_str)
        repo = gh_client.get_repo(repo_name_str)

        print("🚀 DEBUG: Fetching open pull requests...")
        open_prs = list(repo.get_pulls(state='open', sort='created', direction='asc'))
        print(f"📊 DEBUG: Found {len(open_prs)} open PRs.")

        if len(open_prs) == 0:
            print("😴 No PRs to review.")
        else:
            print("🚀 DEBUG: Initializing ReviewAgent...")
            agent = ReviewAgent(repo_path=cwd, github_client=gh_client)

            print("🔥 DEBUG: Starting processing...")
            agent.process_open_prs(open_prs)
            print("✅ DEBUG: Process finished.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
