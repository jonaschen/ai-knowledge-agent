import os
import subprocess
import logging
import sys
from github import Github
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import datetime
from langchain_google_vertexai import ChatVertexAI

# Load environment variables
load_dotenv()

class FailureAnalysis(BaseModel):
    """Data model for structured failure analysis."""
    error_type: str = Field(description="The specific Python error type, e.g., 'AssertionError', 'PydanticValidationError'.")
    root_cause: str = Field(description="A concise, one-sentence explanation of the underlying problem.")
    fix_suggestion: str = Field(description="An actionable instruction for the developer to fix the issue.")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReviewAgent:
    def __init__(self, repo_path: str, github_client):
        self.repo_path = repo_path
        self.github_client = github_client
        self.llm = ChatVertexAI(model_name="gemini-1.5-flash")

    def analyze_failure(self, test_output: str) -> FailureAnalysis:
        """Analyzes pytest failure output using a structured LLM to find the root cause."""
        structured_llm = self.llm.with_structured_output(FailureAnalysis)

        prompt_text = (
            "You are a senior QA engineer. Your task is to analyze the following pytest failure log and "
            "determine the root cause. Provide a concise, one-sentence explanation of the problem and a "
            "clear, actionable suggestion for the developer. Respond with a JSON object that strictly "
            "adheres to the `FailureAnalysis` schema."
        )

        # The `invoke` method can take a simple string or a list of messages.
        structured_llm = self.llm.with_structured_output(FailureAnalysis)
        analysis = structured_llm.invoke(f"{prompt_text}\n\n---\n\n{test_output}")

        return analysis

    def write_history(self, pr_number: int, analysis: FailureAnalysis):
        """Appends a structured analysis of a test failure to the history file."""
        log_entry = (
            f"## [PR #{pr_number}] ReviewAgent Failure\n"
            f"- **Date**: {datetime.date.today().isoformat()}\n"
            f"- **Error Type**: {analysis.error_type}\n"
            f"- **Root Cause**: {analysis.root_cause}\n"
            f"- **Fix Suggestion**: {analysis.fix_suggestion}\n"
            f"- **Tags**: #review-agent, #{analysis.error_type.lower()}\n\n"
        )
        with open('studio/review_history.md', 'a', encoding='utf-8') as f:
            f.write(log_entry)

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
                        test_output = test_result.stdout + "\n" + test_result.stderr
                        
                        # AI-powered failure analysis
                        logging.info("Analyzing failure with AI...")
                        analysis = self.analyze_failure(test_output)

                        # Log analysis to history
                        self.write_history(pr.number, analysis)

                        # Create a formatted comment for the PR
                        comment_body = (
                            f"## ❌ Automated Review Failed\n\n"
                            f"**ReviewAgent v2.0** has analyzed the test failure and determined the following:\n\n"
                            f"- **Error Type**: `{analysis.error_type}`\n"
                            f"- **Root Cause**: {analysis.root_cause}\n"
                            f"- **Fix Suggestion**: {analysis.fix_suggestion}\n\n"
                            f"Please address the issue and push a new commit."
                        )
                        
                        logging.info(f"Posting analysis to PR #{pr.number}...")
                        pr.create_issue_comment(comment_body)

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
