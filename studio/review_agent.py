# studio/review_agent.py
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
                    #test_result = subprocess.run(['pytest'], capture_output=True, text=True, cwd=self.repo_path)
# 這樣會確保使用當前的 python 環境來跑 pytest
                    test_result = subprocess.run([sys.executable, '-m', 'pytest'], capture_output=True, text=True, cwd=self.repo_path)

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

# ... 上面的 class ReviewAgent 維持不變 ...
if __name__ == '__main__':
    print("🔍 DEBUG: Starting Review Agent...")
    
    # 1. 載入環境變數
    is_loaded = load_dotenv() 
    print(f"🔍 DEBUG: .env loaded? -> {is_loaded}")
    
    # 取得當前路徑 (傳給 agent 用)
    cwd = os.getcwd()
    print(f"🔍 DEBUG: Current working directory -> {cwd}")

    repo_name_str = os.getenv("GITHUB_REPOSITORY")
    token_str = os.getenv("GITHUB_TOKEN")

    # 檢查變數
    if not repo_name_str or not token_str:
        print("❌ ERROR: Missing environment variables! Check .env file.")
        logging.error("GITHUB_REPOSITORY and GITHUB_TOKEN environment variables must be set.")
        exit(1)

    print(f"🔍 DEBUG: Repo Name -> '{repo_name_str}'")
    print(f"🔍 DEBUG: Token -> '{token_str[:4]}***'")

    try:
        # 2. 先建立 Github 客戶端物件 (這是新接口要求的)
        print("🚀 DEBUG: Logging into GitHub...")
        gh_client = Github(token_str)
        
        # 3. 獲取 Repo 物件以取得 PR 列表
        print(f"🚀 DEBUG: Fetching repo '{repo_name_str}'...")
        repo = gh_client.get_repo(repo_name_str)
        
        print("🚀 DEBUG: Fetching open pull requests...")
        open_prs = list(repo.get_pulls(state='open'))
        print(f"📊 DEBUG: Found {len(open_prs)} open PRs.")

        if len(open_prs) == 0:
            print("😴 No PRs to review. Exiting.")
        else:
            # 4. 【關鍵修正】正確初始化 Agent
            # 傳入 repo_path (本地路徑) 和 github_client (已登入的客戶端)
            print("🚀 DEBUG: Initializing ReviewAgent...")
            
            # 這裡就是修正的地方：不再傳 token 字串，而是傳 client 物件
            agent = ReviewAgent(repo_path=cwd, github_client=gh_client)
            
            # 5. 開始處理
            print("🔥 DEBUG: Starting processing...")
            agent.process_open_prs(open_prs)
            print("✅ DEBUG: Process finished.")

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
