
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

    @patch('subprocess.run')
    @patch('studio.review_agent.log_pr_result')
    @patch('studio.review_agent.ReviewAgent.review_code_llm')
    def test_ai_review_is_skipped_when_tests_pass(
        self, mock_review_code_llm, mock_log_pr_result, mock_subprocess_run
    ):
        """
        GIVEN a PR where tests pass
        WHEN the review agent processes it
        THEN the AI code review should be skipped.
        """
        # --- Arrange ---
        mock_subprocess_run.return_value.returncode = 0  # Tests passed

        mock_pr = MagicMock()
        mock_pr.number = 1
        mock_pr.title = "PR 1"
        mock_pr.draft = False

        agent = ReviewAgent(repo_path='.', github_client=None)

        # --- Act ---
        agent.process_open_prs([mock_pr])

        # --- Assert ---
        mock_review_code_llm.assert_not_called()

    @patch('subprocess.run')
    @patch('langchain_google_vertexai.ChatVertexAI')
    def test_review_code_llm_handles_json_decode_error(self, MockChatVertexAI, mock_subprocess_run):
        """
        GIVEN the LLM returns a malformed JSON string
        WHEN the review_code_llm method is called
        THEN it should handle the JSONDecodeError gracefully and return a default value.
        """
        # --- Arrange ---
        mock_subprocess_run.return_value.stdout = "some diff"
        mock_llm_instance = MockChatVertexAI.return_value
        mock_llm_instance.invoke.return_value.content = "This is not JSON"

        agent = ReviewAgent(repo_path='.', github_client=None)
        agent.llm = mock_llm_instance

        # --- Act ---
        result = agent.review_code_llm(MagicMock())

        # --- Assert ---
        self.assertEqual(result, {'approved': True, 'comments': 'AI Review failed due to invalid JSON response.'})
