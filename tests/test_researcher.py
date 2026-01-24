import unittest
from unittest.mock import patch, MagicMock

# The Researcher class does not exist yet, but we write the test as if it does.
from product.researcher import Researcher

class TestResearcher(unittest.TestCase):

    @patch('product.researcher.TavilyClient')
    def test_search_parses_tavily_response(self, MockTavilyClient):
        """
        Tests if the search method correctly calls the Tavily client
        and parses its response into our standard structured format.
        """
        # Arrange: Configure the mock
        mock_api_key = "test_key"
        mock_tavily_instance = MockTavilyClient.return_value
        mock_tavily_instance.search.return_value = {
            "results": [
                {"title": "Test Title 1", "url": "https://example.com/1", "content": "Snippet 1..."},
                {"title": "Test Title 2", "url": "https://example.com/2", "content": "Snippet 2..."}
            ]
        }

        # Act: Instantiate our Researcher and call the search method
        researcher = Researcher(tavily_api_key=mock_api_key)
        results = researcher.search(query="test query", max_results=2)

        # Assert: Verify the interaction and the output
        MockTavilyClient.assert_called_once_with(api_key=mock_api_key)
        mock_tavily_instance.search.assert_called_once_with(query="test query", max_results=2, search_depth="basic")

        expected_results = [
            {'title': 'Test Title 1', 'url': 'https://example.com/1', 'content': 'Snippet 1...'},
            {'title': 'Test Title 2', 'url': 'https://example.com/2', 'content': 'Snippet 2...'}
        ]
        self.assertEqual(results, expected_results)

    @patch('product.researcher.Researcher.search')
    def test_get_book_reviews_uses_specialized_query(self, mock_search):
        """
        Tests if get_book_reviews calls the main search method with a
        correctly formatted query string.
        """
        # Arrange
        researcher = Researcher(tavily_api_key="test_key")
        book_title = "The Pragmatic Programmer"

        # Act
        researcher.get_book_reviews(book_title=book_title)

        # Assert
        expected_query = f'reviews of the book "{book_title}"'
        mock_search.assert_called_once_with(query=expected_query)

def test_search_filters_low_quality_book_sources():
    """
    Given a book-related query is flagged,
    When the search is performed,
    Then the query should be enhanced and low-quality sources should be filtered out.
    """
    # Arrange
    mock_tavily_results = {
        "results": [
            {"url": "https://www.nybooks.com/articles/2022/03/24/the-enigma-of-ai-consciousness/", "content": "Authoritative review..."},
            {"url": "https://www.reddit.com/r/books/comments/12345/any_good_books_on_deep_learning/", "content": "Reddit discussion..."},
            {"url": "https://www.goodreads.com/list/show/123.Best_AI_Books", "content": "A list of books..."},
            {"url": "https://www.theguardian.com/books/2023/jun/01/a-review-of-deep-learning-foundations", "content": "A deep dive..."},
            {"url": "https://www.buzzfeed.com/top-5-ai-books-you-must-read", "content": "A low-content listicle..."},
        ]
    }

    expected_urls = [
        "https://www.nybooks.com/articles/2022/03/24/the-enigma-of-ai-consciousness/",
        "https://www.theguardian.com/books/2023/jun/01/a-review-of-deep-learning-foundations",
    ]

    # Mock the Tavily client's search method
    with patch('product.researcher.TavilyClient') as mock_tavily:
        mock_instance = MagicMock()
        mock_instance.search.return_value = mock_tavily_results
        mock_tavily.return_value = mock_instance

        # Act
        researcher = Researcher()
        # Add a flag to indicate this is a book search for the Curator fallback
        actual_results = researcher.search(topic="deep learning", is_book_search=True)

        # Assert
        # 1. Assert the search query was enhanced for finding books
        mock_instance.search.assert_called_once_with(
            query="best authoritative books on deep learning in-depth review",
            max_results=5
        )

        # 2. Assert the low-quality results are filtered
        actual_urls = [res['url'] for res in actual_results]
        assert len(actual_urls) == len(expected_urls), "The number of filtered results is incorrect."
        assert sorted(actual_urls) == sorted(expected_urls), "The filtered URLs do not match the expected URLs."

if __name__ == '__main__':
    unittest.main()
