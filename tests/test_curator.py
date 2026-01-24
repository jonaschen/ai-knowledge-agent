import unittest
from unittest.mock import MagicMock, patch
import os
import requests

# Set environment variables to avoid defaults that might cause issues (though defaults seem harmless for instantiation)
os.environ["PROJECT_ID"] = "test-project"
os.environ["LOCATION"] = "us-central1"

# Mock ChatVertexAI before importing curator
with patch('langchain_google_vertexai.ChatVertexAI') as MockChatVertexAI:
    from src import curator
from langchain_core.messages import HumanMessage

class TestCurator(unittest.TestCase):
    def setUp(self):
        # Reset the mock llm for each test
        self.mock_llm = curator.llm
        self.mock_llm.invoke.reset_mock()
        # Explicitly clear side_effect to prevent test leakage
        self.mock_llm.invoke.side_effect = None

    def test_prompt_construction_uses_human_message(self):
        """
        Tests that the prompt constructor uses HumanMessage instead of SystemMessage.
        This is a requirement for compatibility with certain models.
        """
        # GIVEN a topic for the prompt
        book = {
            "title": "Quantum Computing",
            "authors": ["Author"],
            "publisher": "Publisher",
            "publishedDate": "2023",
            "description": "A book about quantum computing."
        }
        self.mock_llm.invoke.return_value = MagicMock(content='{"score": 8.0, "reason": "Good"}')

        # WHEN the prompt is constructed by calling the function
        curator.verify_source_reliability(book)

        # THEN the first message in the prompt must be an instance of HumanMessage
        self.assertTrue(self.mock_llm.invoke.called)
        args, _ = self.mock_llm.invoke.call_args
        prompt_messages = args[0]

        assert len(prompt_messages) > 0, "Prompt should have at least one message."
        assert isinstance(prompt_messages[0], HumanMessage), \
            f"Expected first message to be HumanMessage, but got {type(prompt_messages[0])}."

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

    def test_verify_reliability_handles_markdown_wrapped_json(self):
        """
        Ensures verify_source_reliability can parse JSON even when it's wrapped
        in a Markdown code block, which is a known LLM failure mode.
        """
        # Arrange
        book = {
            "title": "Test Book",
            "authors": ["Author"],
            "publisher": "Publisher",
            "publishedDate": "2023",
            "description": "Some description"
        }

        # This string simulates the LLM's faulty output
        markdown_wrapped_json_string = """
        ```json
        {
            "score": 9.5,
            "reason": "The author is a recognized expert in the field."
        }
        ```
        """

        expected_dict = {
            "score": 9.5,
            "reason": "The author is a recognized expert in the field."
        }

        self.mock_llm.invoke.return_value = MagicMock(content=markdown_wrapped_json_string)

        # Act
        result = curator.verify_source_reliability(book)

        # Assert
        self.assertEqual(result, expected_dict, "The method failed to strip Markdown and parse the JSON correctly.")

    def test_search_google_books_fallback_uses_researcher_agent(self):
        """
        Verify that if the primary API fails, the Curator uses the
        Researcher agent as a fallback.
        """
        query = "Principles of Neural Science"

        # Mock the Researcher to control its output and monitor its usage
        mock_researcher_instance = MagicMock()
        mock_researcher_instance.search.return_value = [
            {
                "title": "Principles of Neural Science, Fifth Edition",
                "url": "http://example.com/neural-science",
                "content": "A book by Kandel."
            }
        ]

        # Patch the primary API to simulate a failure
        # AND patch the Researcher to inject our mock
        with patch('requests.get', side_effect=requests.exceptions.RequestException("API Unavailable")) as mock_requests_get, \
             patch('src.curator.Researcher', return_value=mock_researcher_instance) as mock_researcher_class:

            curator_instance = curator
            books = curator_instance.search_google_books(query)

            # 1. Verify the primary API was called and failed
            mock_requests_get.assert_called_once()

            # 2. Verify the Researcher was initialized and its search method was called
            mock_researcher_class.assert_called_once()
            mock_researcher_instance.search.assert_called_once_with(query=query)

            # 3. Verify the Curator correctly maps the Researcher's output
            assert len(books) == 1
            assert books[0]['title'] == "Principles of Neural Science, Fifth Edition"
            assert books[0]['url'] == "http://example.com/neural-science"
            assert books[0]['source'] == "Researcher Fallback" # Verify the source is correctly attributed


if __name__ == '__main__':
    unittest.main()
