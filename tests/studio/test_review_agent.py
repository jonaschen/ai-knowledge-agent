
import unittest
from unittest.mock import patch, call, MagicMock
from studio.review_agent import ReviewAgent # Assuming ReviewAgent is a class

class TestReviewAgentWorkflow(unittest.TestCase):

    @patch('subprocess.run')
    @patch('studio.review_agent.log_pr_result')
    @patch('studio.review_agent.ReviewAgent.review_code_llm')
    def test_review_process_commits_history_to_feature_branch_and_returns_summary(
        self, mock_review_code_llm, mock_log_pr_result, mock_subprocess_run
    ):
        """
        GIVEN a review process is initiated on a feature branch
        WHEN the review agent completes its analysis
        THEN it should commit and push review_history.md to that branch
        AND return a structured summary of the results.
        """
        # --- Arrange ---
        mock_review_code_llm.return_value = {'approved': True}
        mock_subprocess_run.return_value.returncode = 0

        mock_pr1 = MagicMock()
        mock_pr1.number = 1
        mock_pr1.title = "PR 1"
        mock_pr1.draft = False
        mock_pr1.head.ref = "feature/PR-1-new-logic"

        agent = ReviewAgent(repo_path='.', github_client=None)

        # --- Act ---
        summary = agent.process_open_prs([mock_pr1])

        # --- Assert ---
        # 1. Assert the structured summary is correct
        self.assertEqual(summary, {"total_processed": 1, "passed": 1, "failed": 0})

        # 2. Assert the correct git commands were called in order
        expected_git_calls = [
            call(['git', 'add', '-f', 'studio/review_history.md'], check=True, cwd='.', capture_output=True),
            call(['git', 'commit', '-m', 'docs: Update review history for pr-1'], check=True, cwd='.', capture_output=True),
            call(['git', 'push', 'origin', 'pr-1:feature/PR-1-new-logic'], check=True, cwd='.', capture_output=True)
        ]
        mock_subprocess_run.assert_has_calls(expected_git_calls, any_order=False)
