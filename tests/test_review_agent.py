import unittest
from unittest.mock import Mock, patch

# Note: These classes do not exist yet. You will create them in Step 2.
from studio.review_agent import ReviewAgent, RunResult, PolicyResult

class TestReviewAgent(unittest.TestCase):

    def setUp(self):
        # Mock dependencies based on the new architecture
        self.mock_vcs_provider = Mock()
        self.mock_test_runner = Mock()
        self.mock_policy = Mock()

        # Instantiate the agent with mocked dependencies
        self.agent = ReviewAgent(
            vcs_provider=self.mock_vcs_provider,
            test_runner=self.mock_test_runner,
            policies=[self.mock_policy]
        )

    def test_process_pr_success_path(self):
        """
        GIVEN a pull request is ready for review
        WHEN all policies pass and all tests pass
        THEN the agent should merge the PR and post a success comment.
        """
        # Arrange
        pr_id = 123
        pr_data = {
            "id": pr_id,
            "description": "## 🤖 Copilot Consultation Log\n- **Target Function**: `...`\n- **Copilot Advice**: `...`\n- **Result**: `Applied`"
        }
        self.mock_vcs_provider.get_open_prs.return_value = [pr_data]

        # Mock policy check to return success
        self.mock_policy.check.return_value = PolicyResult(passed=True, message="Copilot log found.")

        # Mock test runner to return success
        self.mock_test_runner.run.return_value = RunResult(passed=True, output="All 25 tests passed.")

        # Act
        self.agent.process_open_prs()

        # Assert
        self.mock_vcs_provider.get_open_prs.assert_called_once()
        self.mock_policy.check.assert_called_once_with(pr_data)
        self.mock_test_runner.run.assert_called_once()
        self.mock_vcs_provider.post_comment.assert_called_once_with(pr_id, "✅ All checks passed. Merging PR.")
        self.mock_vcs_provider.merge_pr.assert_called_once_with(pr_id)

    def test_process_pr_test_failure(self):
        """
        GIVEN a pull request is ready for review
        WHEN tests fail
        THEN the agent should post a failure comment and NOT merge the PR.
        """
        # Arrange
        pr_id = 456
        pr_data = {"id": pr_id, "description": "## 🤖 Copilot Consultation Log..."}
        self.mock_vcs_provider.get_open_prs.return_value = [pr_data]
        self.mock_policy.check.return_value = PolicyResult(passed=True, message="Copilot log found.")
        self.mock_test_runner.run.return_value = RunResult(passed=False, output="1 test failed: test_something.")

        # Act
        self.agent.process_open_prs()

        # Assert
        failure_comment = "❌ Checks failed. Please review the logs.\n\n**Test Results:**\n```\n1 test failed: test_something.\n```"
        self.mock_vcs_provider.post_comment.assert_called_once_with(pr_id, failure_comment)
        self.mock_vcs_provider.merge_pr.assert_not_called()

    def test_process_pr_policy_failure(self):
        """
        GIVEN a pull request is ready for review
        WHEN a policy check fails (e.g., missing Copilot log)
        THEN the agent should post a failure comment and NOT run tests or merge the PR.
        """
        # Arrange
        pr_id = 789
        pr_data = {"id": pr_id, "description": "Missing the log."}
        self.mock_vcs_provider.get_open_prs.return_value = [pr_data]
        self.mock_policy.check.return_value = PolicyResult(passed=False, message="Missing Copilot Consultation Log.")

        # Act
        self.agent.process_open_prs()

        # Assert
        failure_comment = "❌ Checks failed. Please review the logs.\n\n**Policy Check:**\nMissing Copilot Consultation Log."
        self.mock_test_runner.run.assert_not_called() # Crucially, tests should not run
        self.mock_vcs_provider.post_comment.assert_called_once_with(pr_id, failure_comment)
        self.mock_vcs_provider.merge_pr.assert_not_called()