import unittest
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock, ANY
from datetime import datetime
import re
import os
import json

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
        self.agent = ReviewAgent(self.mock_repo_path, self.mock_github_client)

        self.pr_id = 101
        self.today = datetime.now().strftime("%Y-%m-%d")

    def test_analyze_failure(self):
        """
        Tests if the agent can parse pytest output into a structured dictionary.
        """
        analysis = self.agent.analyze_failure(MOCK_PYTEST_FAILURE_OUTPUT, self.pr_id)

        self.assertEqual(analysis['pr_id'], self.pr_id)
        self.assertEqual(analysis['component'], 'Curator')
        self.assertEqual(analysis['error_type'], 'APITimeout Handling Error')
        self.assertIn("Failed: DID NOT RAISE", analysis['root_cause'])
        self.assertIn("tests/test_curator.py", analysis['root_cause'])

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    def test_write_history(self, mock_file, mock_makedirs, mock_exists):
        """
        Tests if the agent formats and appends the failure log correctly.
        """
        with patch.dict(os.environ, {"UPDATE_REVIEW_HISTORY": "true"}):
            # Mock exists to avoid file system interaction
            mock_exists.return_value = True

            # Step 1: Define a pre-canned analysis dictionary
            analysis = {
                'pr_id': self.pr_id,
                'component': 'Curator',
                'error_type': 'APITimeout Handling Error',
                'root_cause': "Failed: DID NOT RAISE <class 'product.curator.APITimeout'> in tests/test_curator.py",
                'fix_pattern': "Ensure custom exceptions are properly raised and caught in tests. Use `pytest.raises` context manager correctly.",
                'tags': "#mocking, #api, #timeout"
            }

            # Step 2: Write the history
            self.agent.write_history(analysis)

            # Step 4: Verify the output format
        # Verify open was called
        mock_file.assert_called()
        handle = mock_file()

        expected_content = f"""
## [PR #101] Curator Failure
- **Date**: {self.today}
- **Error Type**: APITimeout Handling Error
- **Root Cause**: Failed: DID NOT RAISE <class 'product.curator.APITimeout'> in tests/test_curator.py
- **Fix Pattern**: Ensure custom exceptions are properly raised and caught in tests. Use `pytest.raises` context manager correctly.
- **Tags**: #mocking, #api, #timeout
"""
        # Get the written content and normalize whitespace
        written_content = handle.write.call_args[0][0]
        self.assertEqual(
            re.sub(r'\s+', ' ', written_content).strip(),
            re.sub(r'\s+', ' ', expected_content).strip()
        )

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

class TestReviewAgentResilience(unittest.TestCase):

    def setUp(self):
        # Mock dependencies for ReviewAgent
        self.mock_repo_path = "/tmp/mock_repo"
        self.mock_github_client = MagicMock()
        self.agent = ReviewAgent(self.mock_repo_path, self.mock_github_client)

    @patch('studio.review_agent.ReviewAgent._call_ai_for_review')
    def test_handle_empty_ai_response_gracefully(self, mock_call_ai):
        """
        Test that ReviewAgent does not crash when the AI returns an empty string.
        This simulates a JSONDecodeError scenario.
        """
        # Arrange: Simulate the AI returning an empty, non-JSON string
        mock_call_ai.return_value = ""

        # Act: Run the review process
        # We expect this to fail with a JSONDecodeError before the fix
        # and handle it gracefully after the fix.
        try:
            result = self.agent.review_pr_code("dummy code")
            # Assert: After the fix, the agent should return a specific error state, not crash.
            self.assertIn("error", result)
            self.assertEqual(result["error"], "AI response was not valid JSON.")
        except json.JSONDecodeError:
            self.fail("ReviewAgent crashed with JSONDecodeError instead of handling it.")

if __name__ == "__main__":
    unittest.main()
