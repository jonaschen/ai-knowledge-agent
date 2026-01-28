import unittest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, ANY
from datetime import datetime
import re
import os
import json
import sys

# Add repo root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from studio.review_agent import ReviewAgent

# Sample pytest failure output for a hypothetical PR #101
MOCK_PYTEST_FAILURE_OUTPUT = """
============================= test session starts ==============================
...
collected 1 item

tests/test_curator.py F                                                  [100%]

=================================== FAILURES ===================================
___________________________ test_curator_api_timeout ___________________________

    def test_curator_api_timeout():
        # Simulate a Google Books API timeout
        with patch('product.curator.requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout
>           with pytest.raises(APITimeout):
E           Failed: DID NOT RAISE <class 'product.curator.APITimeout'>
tests/test_curator.py:42: Failed
=========================== short test summary info ============================
FAILED tests/test_curator.py::test_curator_api_timeout - Failed: DID NOT RAI...
============================== 1 failed in 0.12s ===============================
"""

class TestReviewAgent(unittest.TestCase):

    def setUp(self):
        # Mock dependencies for ReviewAgent
        self.mock_repo_path = "/tmp/mock_repo"
        self.mock_github_client = MagicMock()

        # Patch ChatVertexAI to avoid real network calls during init
        with patch('studio.review_agent.ChatVertexAI') as MockLLM:
             self.mock_llm_instance = MockLLM.return_value
             self.agent = ReviewAgent(self.mock_repo_path, self.mock_github_client)
             # Manually assign mock llm just in case
             self.agent.llm = self.mock_llm_instance

        self.pr_id = 101
        self.today = datetime.now().strftime("%Y-%m-%d")

    def test_check_copilot_compliance(self):
        """Test the compliance check for Copilot Log."""
        # Case 1: Missing Body
        pr = MagicMock()
        pr.body = None
        self.assertFalse(self.agent.check_copilot_compliance(pr))

        # Case 2: Missing Log
        pr.body = "Some description but no log."
        self.assertFalse(self.agent.check_copilot_compliance(pr))

        # Case 3: Present Log
        pr.body = "Description.\n\n## 🤖 Copilot Consultation Log\nDetails..."
        self.assertTrue(self.agent.check_copilot_compliance(pr))

    @patch('studio.review_agent.subprocess.run')
    @patch('studio.review_agent.open', new_callable=mock_open, read_data="Mock Rules")
    @patch('os.path.exists', return_value=True)
    def test_review_code_llm_approved(self, mock_exists, mock_file, mock_subprocess):
        """Test AI Review when code is approved."""
        # Setup Git Diff Output
        mock_subprocess.return_value.stdout = "diff --git a/file.py b/file.py\n+ new code"

        # Setup LLM Response
        mock_response = MagicMock()
        mock_response.content = json.dumps({"approved": True, "comments": "LGTM"})
        self.agent.llm.invoke.return_value = mock_response

        # Run
        pr = MagicMock()
        result = self.agent.review_code_llm(pr)

        # Verify
        self.assertTrue(result['approved'])
        self.assertEqual(result['comments'], "LGTM")
        self.agent.llm.invoke.assert_called_once()

    @patch('studio.review_agent.subprocess.run')
    def test_review_code_llm_rejected(self, mock_subprocess):
        """Test AI Review when code is rejected."""
        mock_subprocess.return_value.stdout = "diff ... critical bug"

        mock_response = MagicMock()
        mock_response.content = json.dumps({"approved": False, "comments": "Critical bug found."})
        self.agent.llm.invoke.return_value = mock_response

        pr = MagicMock()
        result = self.agent.review_code_llm(pr)

        self.assertFalse(result['approved'])
        self.assertIn("Critical bug", result['comments'])

    @patch('studio.review_agent.subprocess.run')
    def test_process_open_prs_success_merge(self, mock_subprocess):
        """Test full flow: Compliance OK -> AI OK -> Tests OK -> Merge."""
        # Setup PR
        pr = MagicMock()
        pr.number = 1
        pr.body = "## 🤖 Copilot Consultation Log"
        pr.draft = False

        # Mock subprocess calls
        # 1. git fetch, checkout -> success
        # 2. git diff -> "diff"
        # 3. pytest -> success (returncode 0)
        # 4. cleanup -> success

        def subprocess_side_effect(args, **kwargs):
            cmd = args if isinstance(args, list) else args.split()
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = ""
            if "diff" in cmd:
                mock_res.stdout = "some diff"
            if "pytest" in cmd:
                mock_res.returncode = 0
            return mock_res

        mock_subprocess.side_effect = subprocess_side_effect

        # Mock AI Response
        mock_response = MagicMock()
        mock_response.content = json.dumps({"approved": True, "comments": "LGTM"})
        self.agent.llm.invoke.return_value = mock_response

        # Run
        self.agent.process_open_prs([pr])

        # Verify Merge Called
        pr.merge.assert_called_once()
        pr.create_issue_comment.assert_not_called()

    @unittest.skip("Compliance check is currently disabled in the code.")
    @patch('studio.review_agent.subprocess.run')
    def test_process_open_prs_compliance_failure(self, mock_subprocess):
        """Test flow: Compliance Fail -> No AI/Test -> Comment."""
        pr = MagicMock()
        pr.number = 2
        pr.body = "No log here."
        pr.draft = False

        # Mock subprocess just in case (fetch/checkout still happen)
        # Mock AI to return True (so we isolate compliance failure)
        mock_response = MagicMock()
        mock_response.content = json.dumps({"approved": True, "comments": "LGTM"})
        self.agent.llm.invoke.return_value = mock_response

        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = ""

        self.agent.process_open_prs([pr])

        # Verify
        pr.merge.assert_not_called()
        pr.create_issue_comment.assert_called_once()
        comment = pr.create_issue_comment.call_args[0][0]
        self.assertIn("Compliance Violation", comment)

    def test_agent_can_commit_ignored_history_file(self):
        """
        Ensures the ReviewAgent can force-add the ignored review_history.md file.
        This test will fail before the fix is applied.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            studio_dir = repo_path / "studio"
            studio_dir.mkdir()

            # Initialize Git repo and make initial commit
            subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, check=True)
            (repo_path / ".gitignore").write_text("studio/review_history.md\n")
            (studio_dir / "review_history.md").write_text("## [PR #101] A test failure")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
            subprocess.run(["git", "commit", "-m", "initial commit"], cwd=repo_path, check=True, capture_output=True)

            # The agent operates on a local branch representing the PR
            local_pr_branch = "pr-101"
            subprocess.run(["git", "checkout", "-b", local_pr_branch], cwd=repo_path, check=True)

            # Create a mock PR object that mimics the GitHub PR structure
            mock_pr = MagicMock()
            mock_pr.number = 101
            mock_pr.head.ref = "feature-branch-name" # The name of the branch in the remote fork

            # Instantiate the agent with the temporary repo path
            agent = ReviewAgent(repo_path=str(repo_path), github_client=self.mock_github_client)

            # Call the method under test.
            # Before the fix, this will log an error but not raise, and no commit will be made.
            # The push command will also fail because there's no remote, which is also caught.
            agent._commit_review_history(mock_pr, local_pr_branch)

            # Verify that the commit was NOT made (this is the state before the fix)
            # To create a failing test, we assert that the commit *was* made.
            log_output = subprocess.run(
                ["git", "log", "--oneline"],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True
            ).stdout

            # This assertion will fail before the fix, creating our "Red" state.
            self.assertIn(f"docs: update review history for PR #{mock_pr.number}", log_output)

if __name__ == "__main__":
    unittest.main()
