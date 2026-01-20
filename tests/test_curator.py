import unittest
from unittest.mock import MagicMock, patch
import os

# Set environment variables to avoid defaults that might cause issues (though defaults seem harmless for instantiation)
os.environ["PROJECT_ID"] = "test-project"
os.environ["LOCATION"] = "us-central1"

# Mock ChatVertexAI before importing curator
with patch('langchain_google_vertexai.ChatVertexAI') as MockChatVertexAI:
    from src import curator

class TestCurator(unittest.TestCase):
    def setUp(self):
        # Reset the mock llm for each test
        self.mock_llm = curator.llm
        self.mock_llm.invoke.reset_mock()

    def test_verify_reliability_empty_description(self):
        """
        Test that verify_source_reliability handles empty description
        and constructs a prompt with a fallback message.
        """
        book = {
            "title": "Test Book",
            "authors": ["Author One"],
            "publisher": "Test Publisher",
            "publishedDate": "2023",
            "description": ""  # Empty description
        }

        # Mock successful response
        self.mock_llm.invoke.return_value = MagicMock(content='{"score": 8.0, "reason": "Good"}')

        curator.verify_source_reliability(book)

        # Verify that llm.invoke was called
        self.assertTrue(self.mock_llm.invoke.called)

        # Get the arguments passed to invoke
        args, _ = self.mock_llm.invoke.call_args
        # args[0] is a list of messages
        messages = args[0]
        system_msg_content = messages[0].content

        # We expect the prompt to contain "No description available" or similar handling
        # Currently it probably contains "Description: " with empty string.
        # This assertion is expected to FAIL before the fix.
        self.assertIn("No description available", system_msg_content,
                      "Prompt should handle empty description explicitly")

    def test_verify_reliability_handles_exception(self):
        """Test that the function catches exceptions (e.g. 400 error)"""
        book = {
            "title": "Test Book",
            "authors": ["Author"],
            "publisher": "Publisher",
            "publishedDate": "2023",
            "description": "Some description"
        }

        # Simulate exception
        self.mock_llm.invoke.side_effect = Exception("400 Bad Request")

        result = curator.verify_source_reliability(book)

        self.assertEqual(result["score"], 5.0)
        self.assertIn("Verification failed", result["reason"])

if __name__ == '__main__':
    unittest.main()
