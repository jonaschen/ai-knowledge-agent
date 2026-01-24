import unittest
from unittest.mock import patch, MagicMock

# The test assumes the refactored pm.py will have a class named ProductManager
# and a method to generate the plan, e.g., generate_plan()
from studio.pm import ProductManager

class TestProductManager(unittest.TestCase):

    @patch('studio.pm.load_dotenv')
    @patch('studio.pm.ChatVertexAI')
    def test_initialization_and_model_usage(self, mock_chat_vertex_ai, mock_load_dotenv):
        """
        Tests that the ProductManager initializes correctly, loads environment variables,
        and uses the specified ChatVertexAI model.
        """
        # Arrange
        mock_llm_instance = MagicMock()
        mock_chat_vertex_ai.return_value = mock_llm_instance

        # Act
        pm = ProductManager()
        # We assume a method like 'generate_plan' will be the one invoking the LLM
        pm.generate_plan("some user requirement")

        # Assert
        # 1. Ensure environment variables are loaded
        mock_load_dotenv.assert_called_once()

        # 2. Ensure ChatVertexAI was initialized with the correct model
        mock_chat_vertex_ai.assert_called_once_with(
            model="gemini-2.5-pro",
            temperature=0.0
        )

        # 3. Ensure the LLM's 'invoke' method was called
        mock_llm_instance.invoke.assert_called_once()
        print("\n[Test Succeeded] ProductManager correctly uses ChatVertexAI with gemini-2.5-pro.")


if __name__ == '__main__':
    unittest.main()
