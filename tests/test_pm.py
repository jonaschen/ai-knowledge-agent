import pytest
from unittest.mock import patch, MagicMock
from studio.pm import ProductManager

@patch('studio.pm.load_dotenv')
@patch('studio.pm.ChatVertexAI')
def test_initialization_and_model_usage(mock_chat_vertex_ai, mock_load_dotenv):
    """
    Tests that the ProductManager initializes correctly, loads environment variables,
    and uses the specified ChatVertexAI model.
    """
    # Arrange
    mock_llm_instance = MagicMock()
    mock_chat_vertex_ai.return_value = mock_llm_instance

    # Act
    pm = ProductManager()

    # Assert
    mock_load_dotenv.assert_called_once()
    mock_chat_vertex_ai.assert_called_once_with(
        model_name="gemini-1.5-pro",
        temperature=0.0
    )
    assert pm.chain is not None
