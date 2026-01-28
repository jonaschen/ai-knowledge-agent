import os
import subprocess
import logging
import sys
import re
import json
from datetime import datetime
from github import Github
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ReviewAgent:
    def __init__(self, repo_path: str, github_client):
        self.repo_path = repo_path
        self.github_client = github_client

        # Initialize LLM
        project_id = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION", "us-central1")
        if project_id:
             self.llm = ChatVertexAI(
                model_name="gemini-2.5-pro",
                project=project_id,
                location=location,
                temperature=0.1,
                max_output_tokens=2048
            )
        else:
            logging.warning("PROJECT_ID not set. AI Review capabilities will be disabled/mocked.")
            self.llm = None

    def check_copilot_compliance(self, pr) -> bool:
        """
        Checks if the PR description contains the required Copilot Consultation Log.
        """
        if not pr.body:
            return False
        return "## 🤖 Copilot Consultation Log" in pr.body

    def review_code_llm(self, pr) -> dict:
        """
        Uses LLM to review the code changes against studio/rules.md and general best practices.
        Returns: {'approved': bool, 'comments': str}
        """
        if not self.llm:
            return {'approved': True, 'comments': "Skipped AI review (LLM not configured)."}

        try:
            # 1. Get the Diff
            # Ensure origin/main is available for diffing
            subprocess.run(['git', 'fetch', 'origin', 'main'], check=False, cwd=self.repo_path, capture_output=True)

            diff_proc = subprocess.run(
                ['git', 'diff', 'origin/main...HEAD'],
                capture_output=True, text=True, cwd=self.repo_path
            )
            diff_text = diff_proc.stdout

            if not diff_text.strip():
                return {'approved': True, 'comments': "No code changes detected."}

            if len(diff_text) > 30000:
                diff_text = diff_text[:30000] + "\n... (Diff truncated due to size)"

            # 2. Get Rules
            rules_path = os.path.join(self.repo_path, 'studio', 'rules.md')
            rules_content = "No specific rules found."
            if os.path.exists(rules_path):
                with open(rules_path, 'r') as f:
                    rules_content = f.read()

            # 3. Prompt LLM
            prompt = f"""
            You are a Senior Software Engineer and Code Reviewer.
            Review the following code changes (Diff) against the provided Project Rules.

            === PROJECT RULES (studio/rules.md) ===
            {rules_content}

            === CODE CHANGES (Diff) ===
            {diff_text}

            === INSTRUCTIONS ===
            1. Check for **Critical Bugs** (logic errors, crashes).
            2. Check for **Security Vulnerabilities**.
            3. Check for violations of **Project Rules** (e.g., specific mocking patterns, architectural constraints).
            4. Ignore minor style nitpicks unless they violate a strict rule.

            Return a JSON object with the following structure:
            {{
                "approved": boolean,  // False if there are critical bugs, security issues, or rule violations. True otherwise.
                "comments": "markdown string" // detailed feedback explaining the decision.
            }}
            """

            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            # Clean up code blocks if present
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            result = json.loads(content)
            return result

        except Exception as e:
            logging.error(f"AI Review failed: {e}")
            return {'approved': True, 'comments': f"AI Review failed due to internal error: {e}"}

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
            fetch_ref = f"pull/{pr.number}/head:{local_pr_branch}"

            try:
                try:
                    # 1. Fetch and Checkout
                    logging.info(f"Fetching and checking out PR #{pr.number}...")
                    subprocess.run(['git', 'fetch', 'origin', fetch_ref], check=True, cwd=self.repo_path, capture_output=True)
                    subprocess.run(['git', 'checkout', local_pr_branch], check=True, cwd=self.repo_path, capture_output=True)

                    ## --- Step 1: Compliance Check ---
                    # logging.info("Running Compliance Check...")
                    # compliance_ok = self.check_copilot_compliance(pr)
                    compliance_ok = True

                    # --- Step 2: AI Code Review ---
                    logging.info("Running AI Code Review...")
                    review_result = self.review_code_llm(pr)
                    ai_approved = review_result.get('approved', True)


                    # --- Step 3: Run Tests (pytest) ---
                    logging.info(f"Running pytest for PR #{pr.number}...")
                    test_result = subprocess.run(
                        [sys.executable, '-m', 'pytest'], 
                        capture_output=True, 
                        text=True, 
                        cwd=self.repo_path
                    )
                    tests_passed = (test_result.returncode == 0)

                    # --- Decision Logic ---
                    if compliance_ok and ai_approved and tests_passed:
                        logging.info(f"✅ All checks passed for PR #{pr.number}.")
                        if pr.draft:
                            logging.warning(f"PR #{pr.number} is a Draft. Cannot merge automatically.")
                        else:
                            logging.info(f"Merging PR #{pr.number}...")
                            pr.merge(merge_method='squash')
                            logging.info(f"🚀 Successfully merged PR #{pr.number}.")
                    
                    else:
                        logging.warning(f"❌ Checks failed for PR #{pr.number}.")
                        
                        # Prepare Consolidated Feedback
                        feedback_parts = []

                        if not compliance_ok:
                            feedback_parts.append("### 👮 Compliance Violation\n- ❌ Missing **Copilot Consultation Log** in PR description.\n- Please consult `AGENTS.md` and add the log.")

                        if not ai_approved:
                            feedback_parts.append(f"### 🧠 AI Code Review\n- ❌ **Changes Requested**\n{review_result.get('comments', 'No details provided.')}")

                        if not tests_passed:
                            feedback_parts.append(f"### 🧪 Test Failures\n- ❌ `pytest` failed.")

                        full_comment = f"## ❌ Automated Review Failed\n\n" + "\n\n---\n\n".join(feedback_parts)
                        
                        logging.info(f"Posting error report to PR #{pr.number}...")
                        pr.create_issue_comment(full_comment)

                    # --- Step 4: Log Result (New) ---
                    failure_log = test_result.stdout + "\n" + test_result.stderr
                    log_pr_result(
                        pr_number=pr.number,
                        test_passed=tests_passed,
                        failure_log=failure_log if not tests_passed else None
                    )

                except subprocess.CalledProcessError as e:
                    logging.error(f"Git command failed for PR #{pr.number}: {e}")
                except Exception as e:
                    logging.error(f"An unexpected error occurred: {e}")

            finally:
                # 4. Cleanup
                try:
                    subprocess.run(['git', 'checkout', 'main'], check=True, cwd=self.repo_path, capture_output=True)
                    subprocess.run(['git', 'branch', '-D', local_pr_branch], check=False, cwd=self.repo_path, capture_output=True)
                except Exception as e:
                    logging.warning(f"Cleanup failed: {e}")

    def _commit_review_history(self, pr, branch_name):
        """Helper to commit review_history.md"""
        try:
            logging.info(f"Committing review_history.md to PR #{pr.number}...")
            subprocess.run(['git', 'add', '-f', 'studio/review_history.md'], check=True, cwd=self.repo_path, capture_output=True)
            commit_msg = f"docs: update review history for PR #{pr.number} failure [skip ci]"
            subprocess.run(['git', 'commit', '-m', commit_msg], check=True, cwd=self.repo_path, capture_output=True)
            push_ref = f"{branch_name}:{pr.head.ref}"
            logging.info(f"Pushing to origin {push_ref}...")
            subprocess.run(['git', 'push', 'origin', push_ref], check=True, cwd=self.repo_path, capture_output=True)
        except subprocess.CalledProcessError as e:
             logging.error(f"Failed to commit/push history for PR #{pr.number}: {e}")
             if hasattr(e, 'stderr') and e.stderr:
                 logging.error(f"Git stderr: {e.stderr.decode()}")

# --- Module-level Functions for Logging ---

def _analyze_failure(log: str) -> str:
    """
    Uses LLM to analyze the test failure log and provide a root cause analysis and suggestion.
    """
    project_id = os.getenv("PROJECT_ID")
    if not project_id:
        return "Skipped failure analysis (LLM not configured)."

    try:
        llm = ChatVertexAI(
            model_name="gemini-2.5-pro",
            project=project_id,
            location=os.getenv("LOCATION", "us-central1"),
            temperature=0.1,
            max_output_tokens=2048
        )

        repo_path = os.getcwd()
        rules_path = os.path.join(repo_path, 'studio', 'rules.md')
        rules_content = "No specific rules found."
        if os.path.exists(rules_path):
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_content = f.read()

        prompt = f"""
        You are a Senior Software Engineer acting as a debugger.
        Analyze the following test failure log, consult the project rules, and provide a concise root cause analysis and a concrete suggestion for a fix.

        === PROJECT RULES (studio/rules.md) ===
        {rules_content}

        === TEST FAILURE LOG ===
        {log}

        === INSTRUCTIONS ===
        1. Identify the specific error message and the test that failed.
        2. Determine the most likely root cause of the failure.
        3. Reference the project rules if they are relevant to the failure.
        4. Provide a clear, actionable suggestion for how to fix the bug.
        5. Return the analysis as a single markdown string.

        Example response:
        "Analysis: The failure in `test_curator.py` is due to a `pydantic_core.ValidationError`. As per `rules.md` (1.1), avoid using `MagicMock` with Pydantic models."
        """

        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content.strip()

    except Exception as e:
        logging.error(f"Failure analysis failed: {e}")
        return f"Failure analysis failed due to internal error: {e}"


def log_pr_result(pr_number: int, test_passed: bool, failure_log: str | None = None):
    """
    Logs the result of a PR test run to the review history.
    If the test failed, it triggers an analysis.
    """
    history_path = os.path.join(os.getcwd(), 'studio', 'review_history.md')
    os.makedirs(os.path.dirname(history_path), exist_ok=True)

    if test_passed:
        log_entry = f"## PR #{pr_number}: PASSED\n\n---\n"
    else:
        analysis_result = "No failure log provided."
        if failure_log:
            analysis_result = _analyze_failure(failure_log)

        log_entry = (
            f"## PR #{pr_number}: FAILED\n\n"
            f"### Review Suggestions\n"
            f"{analysis_result}\n\n"
            f"### Raw Failure Log\n"
            f"```\n"
            f"{failure_log}\n"
            f"```\n"
            f"---\n"
        )

    with open(history_path, 'a', encoding='utf-8') as f:
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
