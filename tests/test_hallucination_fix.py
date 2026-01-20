
import unittest
from unittest.mock import MagicMock, patch, ANY
from typing import TypedDict

# Mock needed modules before importing analyst_core
with patch('langchain_google_vertexai.ChatVertexAI') as MockChatVertexAI:
    import analyst_core

class TestHallucinationFix(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        analyst_core.llm = self.mock_llm

    def test_critique_receives_original_text(self):
        """Test that critique_node receives original_text in the prompt"""

        state = {
            "original_text": "The quick brown fox jumps over the lazy dog.",
            "draft_analysis": "The system architecture involves a fast fox module.",
            "revision_count": 1,
            "book_type": "narrative"
        }

        # Run the critique node directly
        analyst_core.critique_node(state)

        # Get the arguments passed to llm.invoke
        # call_args[0] is positional args. invoke takes a list of messages as the first arg.
        # So we want call_args[0][0] which is the list of messages.

        call_args = self.mock_llm.invoke.call_args
        messages = call_args[0][0]

        # Check if any message content contains the original text
        original_text_present = False
        for msg in messages:
            if "The quick brown fox" in msg.content:
                original_text_present = True
                break

        self.assertTrue(original_text_present, "Original text should be present in the critique prompt to prevent hallucination")

if __name__ == '__main__':
    unittest.main()
