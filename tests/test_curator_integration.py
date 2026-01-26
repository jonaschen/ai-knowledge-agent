import pytest
from unittest.mock import patch, MagicMock
from product.curator import app, GoogleBooksSource, TavilySource

@patch('product.curator.verify_source_reliability')
@patch.object(GoogleBooksSource, 'search')
def test_app_invoke_successful_primary_search(mock_google_search, mock_verify_reliability):
    """
    Given a successful primary source search,
    When the app is invoked,
    Then it should return the expected book from the primary source.
    """
    # Arrange
    mock_google_search.return_value = [
        {
            "title": "Test Book from Google",
            "authors": ["Author"],
            "description": "A book from Google."
        }
    ]
    mock_verify_reliability.return_value = {"score": 8.0, "reason": "Good"}


    # Act
    result = app.invoke({"topic": "test"})

    # Assert
    assert result["selected_book"]["title"] == "Test Book from Google"
    mock_google_search.assert_called_once()

@patch('product.curator.verify_source_reliability')
@patch.object(GoogleBooksSource, 'search')
@patch.object(TavilySource, 'search')
def test_app_invoke_fallback_search(mock_tavily_search, mock_google_search, mock_verify_reliability):
    """
    Given a failing primary source and a successful fallback source,
    When the app is invoked,
    Then it should return the expected book from the fallback source.
    """
    # Arrange
    mock_google_search.side_effect = ConnectionError("API is down")
    mock_tavily_search.return_value = [
        {
            "title": "Test Book from Tavily",
            "authors": ["Author"],
            "description": "A book from Tavily."
        }
    ]
    mock_verify_reliability.return_value = {"score": 8.0, "reason": "Good"}

    # Act
    result = app.invoke({"topic": "test"})

    # Assert
    assert result["selected_book"]["title"] == "Test Book from Tavily"
    mock_google_search.assert_called_once()
    mock_tavily_search.assert_called_once()
