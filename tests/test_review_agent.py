# tests/test_review_agent.py
import unittest
from unittest.mock import patch, MagicMock

# We will create the ReviewAgent class in the implementation step
from studio.review_agent import ReviewAgent

class TestReviewAgent(unittest.TestCase):

    @patch('studio.review_agent.subprocess.run')
    @patch('studio.review_agent.Github')
    def test_merge_pr_on_test_success(self, MockGithub, mock_subprocess_run):
        """
        GIVEN an open pull request
        WHEN the tests pass (returncode 0)
        THEN the agent should merge the PR.
        """
        # --- Arrange ---
        # Mock the subprocess to simulate pytest success
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

        # Mock the PyGithub API
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        # --- Act ---
        agent = ReviewAgent(repo_name="test/repo", github_token="fake_token")
        agent.process_open_prs()

        # --- Assert ---
        mock_repo.get_pulls.assert_called_with(state='open')
        mock_subprocess_run.assert_called_with(['pytest'], capture_output=True, text=True)
        mock_pr.merge.assert_called_once()

    @patch('studio.review_agent.subprocess.run')
    @patch('studio.review_agent.Github')
    def test_no_merge_on_test_failure(self, MockGithub, mock_subprocess_run):
        """
        GIVEN an open pull request
        WHEN the tests fail (returncode 1)
        THEN the agent should NOT merge the PR.
        """
        # --- Arrange ---
        # Mock the subprocess to simulate pytest failure
        mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="Failure", stderr="Error")

        # Mock the PyGithub API
        mock_pr = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get_pulls.return_value = [mock_pr]
        MockGithub.return_value.get_repo.return_value = mock_repo

        # --- Act ---
        agent = ReviewAgent(repo_name="test/repo", github_token="fake_token")
        agent.process_open_prs()

        # --- Assert ---
        mock_repo.get_pulls.assert_called_with(state='open')
        mock_subprocess_run.assert_called_with(['pytest'], capture_output=True, text=True)
        mock_pr.merge.assert_not_called()

if __name__ == '__main__':
    unittest.main()
