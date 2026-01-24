import unittest
import pytest
import json
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from studio.pm import ProductManager
from langchain_core.outputs import Generation
from langchain_core.messages import AIMessage

def test_generation_model_handles_mock_incorrectly():
    """
    This test reproduces the Pydantic ValidationError as requested by the user.
    """
    mock_response = MagicMock()
    with pytest.raises(ValidationError):
        Generation(text=mock_response)

class TestProductManager(unittest.TestCase):

    @patch('studio.pm.load_dotenv')
    @patch('studio.pm.ChatVertexAI')
    def test_initialization_and_model_usage(self, mock_chat_vertex_ai, mock_load_dotenv):
        """
        Tests that the ProductManager initializes correctly and handles the LLM
        response as specified by the user's instructions.
        """
        # --- Arrange ---
        # 1. Mock the LLM instance that ChatVertexAI() will return.
        mock_llm_instance = MagicMock()
        mock_chat_vertex_ai.return_value = mock_llm_instance

        # 2. Create the mock LLM response with a .content attribute containing the JSON string.
        mock_llm_response = AIMessage(content='{"plan": ["Step 1: Do this", "Step 2: Do that"]}')

        # 3. Configure the LLM instance's invoke method to return our mock response.
        mock_llm_instance.invoke.return_value = mock_llm_response

        # --- Act ---
        # Initialize ProductManager and call the method under test.
        pm = ProductManager()
        result = pm.generate_plan("some user requirement")

        # --- Assert ---
        # Verify that ChatVertexAI was initialized correctly.
        mock_chat_vertex_ai.assert_called_once_with(
            model="gemini-2.5-pro",
            temperature=0.0
        )

        # Verify that the LLM's invoke method was called.
        mock_llm_instance.invoke.assert_called_once()

        # Verify that the final output is the correctly parsed dictionary.
        expected_plan = json.loads(mock_llm_response.content)
        self.assertEqual(result, expected_plan)

        print("\n[Test Succeeded] ProductManager correctly parsed the mocked LLM response.")

if __name__ == '__main__':
    unittest.main()
