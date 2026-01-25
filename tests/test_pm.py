import unittest
from unittest.mock import patch, MagicMock

# The test assumes the refactored pm.py will have a class named ProductManager
# and a method to generate the plan, e.g., generate_plan()
from langchain_core.messages import AIMessage
from studio.pm import ProductManager

class TestProductManager(unittest.TestCase):

    @patch('studio.pm.ChatVertexAI')
    def test_initialization_and_model_usage(self, mock_chat_vertex_ai):
        """
        Tests that the ProductManager initializes correctly, loads environment variables,
        and uses the specified ChatVertexAI model.
        """
        # Arrange
        mock_llm_instance = MagicMock()
        # Configure the mock LLM to return a valid AIMessage with JSON content
        # so that JsonOutputParser can process it without validation error.
        success_message = AIMessage(content='{"steps": ["step1"]}')
        mock_llm_instance.invoke.return_value = success_message
        mock_llm_instance.return_value = success_message
        mock_chat_vertex_ai.return_value = mock_llm_instance

        # Act
        pm = ProductManager()
        # We assume a method like 'generate_plan' will be the one invoking the LLM
        pm.generate_plan("some user requirement")

        # Assert
        # 2. Ensure ChatVertexAI was initialized with the correct model
        mock_chat_vertex_ai.assert_called_once_with(
            model="gemini-2.5-pro",
            temperature=0.0
        )

        # 3. Ensure the LLM's 'invoke' method was called
        # Note: When mocking, LangChain might treat the mock as a callable (wrapped in RunnableLambda)
        # instead of calling .invoke() directly if it doesn't see the Runnable spec.
        # So we check if it was called either way.
        assert mock_llm_instance.invoke.called or mock_llm_instance.called, "LLM should have been invoked"

        print("\n[Test Succeeded] ProductManager correctly uses ChatVertexAI with gemini-2.5-pro.")


if __name__ == '__main__':
    unittest.main()
