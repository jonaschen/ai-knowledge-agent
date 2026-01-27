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
                model_name="gemini-1.5-pro",
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

                    # --- Step 1: Compliance Check ---
                    logging.info("Running Compliance Check...")
                    compliance_ok = self.check_copilot_compliance(pr)

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

                            # Existing Failure Analysis Logic
                            error_log = test_result.stdout[-2000:] + "\n" + test_result.stderr[-2000:]
                            analysis = self.analyze_failure(error_log, pr.number)
                            # Only attempt to commit history if writing was successful
                            if os.getenv("CI") or os.getenv("UPDATE_REVIEW_HISTORY"):
                                self.write_history(analysis)
                                # Commit history logic (Only if tests failed, we record it)
                                self._commit_review_history(pr, local_pr_branch)
                            else:
                                logging.info("Skipping write/commit of review_history.md (not in CI/enabled).")

                            feedback_parts.append(
                                f"**Analysis**:\n"
                                f"- **Component**: {analysis.get('component', 'Unknown')}\n"
                                f"- **Error Type**: {analysis.get('error_type', 'Unknown')}\n"
                                f"- **Root Cause**: {analysis.get('root_cause', 'Unknown')}\n\n"
                                f"<details>\n<summary>Click to see Error Log</summary>\n\n"
                                f"```text\n{error_log}\n```\n"
                                f"\n</details>"
                            )

                        full_comment = f"## ❌ Automated Review Failed\n\n" + "\n\n---\n\n".join(feedback_parts)
                        
                        logging.info(f"Posting error report to PR #{pr.number}...")
                        pr.create_issue_comment(full_comment)

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
        # Only write to history if running in CI or explicitly enabled
        if not os.getenv("CI") and not os.getenv("UPDATE_REVIEW_HISTORY"):
            logging.info("Skipping write to review_history.md (not in CI and UPDATE_REVIEW_HISTORY not set).")
            return

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
