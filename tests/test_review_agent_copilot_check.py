import unittest
from unittest.mock import MagicMock, patch

from studio.review_agent import ReviewAgent

class TestReviewAgentCompliance(unittest.TestCase):

    def test_detects_copilot_log_on_subsequent_updates(self):
        """
        Tests that the ReviewAgent re-fetches the PR body and finds the
        compliance log after it was initially missing.
        """
        # Mock the GitHub client and PR object
        mock_client = MagicMock()
        mock_pr = MagicMock()
        mock_pr.number = 123

        # --- State 1: PR body is missing the log ---
        pr_body_initial = "## PR Description\n\n- Did some work."

        # --- State 2: PR body is updated with the log ---
        pr_body_updated = (
            "## PR Description\n\n- Did some work.\n\n"
            "## 🤖 Copilot Consultation Log\n"
            "- **Target Function**: some_function\n"
            "- **Copilot Advice**: Use a different algorithm\n"
            "- **Result**: Applied\n"
        )

        # Configure the mock PR's body to change on each update() call
        mock_pr.body = pr_body_initial
        def update_side_effect():
            if mock_pr.update.call_count > 1:
                mock_pr.body = pr_body_updated

        mock_pr.update = MagicMock(side_effect=update_side_effect)

        # Instantiate the agent with the mocked client
        agent = ReviewAgent(repo_path="/tmp/mock_repo", github_client=mock_client)

        # First check: Should fail (return False)
        is_compliant_first_pass = agent.check_copilot_compliance(mock_pr)
        self.assertFalse(is_compliant_first_pass, "Agent should have detected missing log on first pass.")

        # Second check: Simulates the agent re-running on the updated PR
        is_compliant_second_pass = agent.check_copilot_compliance(mock_pr)
        self.assertTrue(is_compliant_second_pass, "Agent failed to detect the log in the updated PR body.")

        # Verify the client was called twice, proving it re-fetched the data
        self.assertEqual(mock_pr.update.call_count, 2, "The PR body should be fetched on each check.")
