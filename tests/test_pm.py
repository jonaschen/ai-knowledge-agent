import unittest
from unittest.mock import patch, MagicMock
import pytest
from pydantic import ValidationError
from langchain_core.outputs import Generation

# The test assumes the refactored pm.py will have a class named ProductManager
# and a method to generate the plan, e.g., generate_plan()
from studio.pm import ProductManager


def test_generation_model_handles_mock_incorrectly():
    """
    This test reproduces the Pydantic ValidationError.
    Pydantic models validate the data type upon instantiation,
    so passing a mock object instead of a string will fail.
    """
    # This is the INCORRECT usage that causes the error
    mock_response = MagicMock()

    with pytest.raises(ValidationError):
        # This line attempts to pass a MagicMock object to a string field,
        # which correctly raises a Pydantic ValidationError.
        Generation(text=mock_response)


class TestProductManager(unittest.TestCase):

    @patch('studio.pm.load_dotenv')
    @patch('studio.pm.ChatVertexAI')
    def test_initialization_and_model_usage(self, mock_chat_vertex_ai, mock_load_dotenv):
        """
        Tests that the ProductManager initializes correctly, loads environment variables,
        and uses the specified ChatVertexAI model.
        """
        # Arrange
        from langchain_core.messages import AIMessage
        mock_llm_instance = MagicMock()
        mock_chat_vertex_ai.return_value = mock_llm_instance

        # Configure the mock LLM to return an AIMessage object. The StrOutputParser
        # will extract the string content before it hits the JsonOutputParser.
        mock_ai_message = AIMessage(content='{"plan": ["Step 1: Do this", "Step 2: Do that"]}')
        mock_llm_instance.invoke.return_value = mock_ai_message


        # Act
        pm = ProductManager()
        result = pm.generate_plan("some user requirement")

        # Assert
        # 1. Ensure environment variables are loaded
        mock_load_dotenv.assert_called_once()

        # 2. Ensure ChatVertexAI was initialized with the correct model
        mock_chat_vertex_ai.assert_called_once_with(
            model="gemini-1.5-pro-preview-0409",
            temperature=0.0
        )

        # 3. Ensure the LLM's 'invoke' method was called
        mock_llm_instance.invoke.assert_called_once()

        # 4. Assert that the output is correctly parsed dictionary
        self.assertIsInstance(result, dict)
        self.assertIn("plan", result)
        self.assertEqual(len(result["plan"]), 2)


if __name__ == '__main__':
    unittest.main()
