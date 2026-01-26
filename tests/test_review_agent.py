import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime
import re
import os

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

if __name__ == "__main__":
    unittest.main()
