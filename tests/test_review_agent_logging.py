
import unittest
from unittest.mock import patch, mock_open
from studio import review_agent

# A sample failure log that the manager would pass to the review agent
SAMPLE_FAILURE_LOG = """
============================= test session starts ==============================
...
tests/test_curator.py:25: AssertionError
=========================== 1 failed in 0.12s ============================
"""

class TestReviewAgentLogging(unittest.TestCase):
    def test_log_pr_result_success(self):
        """
        Verify that a successful PR test run is logged correctly.
        """
        pr_number = 42
        expected_output = "## PR #42: PASSED\n\n---\n"

        # Mock open() to capture the write operation
        m = mock_open()
        with patch("builtins.open", m):
            review_agent.log_pr_result(
                repo_path="/app",
                pr_number=pr_number,
                test_passed=True
            )

        # Assert that the file was opened in append mode and the correct content was written
        m.assert_called_once_with('/app/studio/review_history.md', 'a', encoding='utf-8')
        handle = m()
        handle.write.assert_called_once_with(expected_output)

    def test_log_pr_result_failure(self):
        """
        Verify that a failed PR test run triggers analysis and logs suggestions.
        """
        pr_number = 43
        # Mock the internal analysis function to return a predictable suggestion
        mock_analysis_result = "Analysis: The failure in `test_curator.py` is due to a `pydantic_core.ValidationError`. As per `rules.md` (1.1), avoid using `MagicMock` with Pydantic models."

        expected_output = (
            "## PR #43: FAILED\n\n"
            "### Review Suggestions\n"
            f"{mock_analysis_result}\n\n"
            "### Raw Failure Log\n"
            "```\n"
            f"{SAMPLE_FAILURE_LOG}\n"
            "```\n"
            "---\n"
        )

        m = mock_open()
        with patch("builtins.open", m), \
             patch("studio.review_agent._analyze_failure", return_value=mock_analysis_result) as mock_analyze:

            review_agent.log_pr_result(
                repo_path="/app",
                pr_number=pr_number,
                test_passed=False,
                failure_log=SAMPLE_FAILURE_LOG
            )
            mock_analyze.assert_called_once_with("/app", SAMPLE_FAILURE_LOG)

        m.assert_called_once_with('/app/studio/review_history.md', 'a', encoding='utf-8')
        handle = m()
        handle.write.assert_called_once_with(expected_output)
