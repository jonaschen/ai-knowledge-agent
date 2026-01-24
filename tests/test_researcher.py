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

    @patch('product.researcher.TavilyClient')
    def test_search_filters_low_quality_book_sources(self, MockTavilyClient):
        """
        Tests that the search method filters out low-quality sources like social media.
        """
        # Arrange
        mock_api_key = "test_key"
        mock_tavily_instance = MockTavilyClient.return_value
        mock_tavily_instance.search.return_value = {
            "results": [
                {"title": "Good Source", "url": "https://www.goodreads.com/book/show/123", "content": "A review."},
                {"title": "Bad Source", "url": "https://twitter.com/some_user/status/123", "content": "A tweet."},
                {"title": "Another Good Source", "url": "https://en.wikipedia.org/wiki/A_Book", "content": "An article."}
            ]
        }
        researcher = Researcher(tavily_api_key=mock_api_key)

        # Act
        results = researcher.search(query="some book")

        # Assert
        # This assertion is expected to fail until the filtering logic is implemented in Researcher.search()
        expected_urls = ["https://www.goodreads.com/book/show/123", "https://en.wikipedia.org/wiki/A_Book"]
        actual_urls = [result['url'] for result in results]

        self.assertCountEqual(actual_urls, expected_urls, "The search results should not contain low-quality sources.")

if __name__ == '__main__':
    unittest.main()
