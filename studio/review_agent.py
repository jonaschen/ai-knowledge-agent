import os
import subprocess
import logging
import sys
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
                        
                        # --- [NEW] Feedback Loop: Comment on GitHub ---
                        error_log = test_result.stdout[-2000:] + "\n" + test_result.stderr[-2000:] # 取最後 2000 字避免太長
                        comment_body = (
                            f"## ❌ Automated Review Failed\n\n"
                            f"**ReviewAgent** ran tests and found errors. Please fix them and push a new commit.\n\n"
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
        open_prs = list(repo.get_pulls(state='open'))
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
