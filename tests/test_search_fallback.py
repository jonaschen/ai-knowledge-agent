
import unittest
from unittest.mock import patch, MagicMock
import requests
from src.curator import search_google_books

class TestSearchFallback(unittest.TestCase):

    @patch('src.curator.TavilyClient')
    @patch('src.curator.requests.get')
    def test_google_books_api_failure_triggers_tavily_fallback(self, mock_requests_get, mock_tavily_client):
        # 1. RED: Setup the failure condition for Google Books API
        mock_google_response = MagicMock()
        mock_google_response.status_code = 429
        mock_google_response.json.return_value = {"error": "Quota Exceeded"}
        mock_requests_get.return_value = mock_google_response

        # 2. Setup the mock for the Tavily fallback
        mock_tavily_search_results = {
            "results": [
                {
                    "title": "Thinking, Fast and Slow",
                    "url": "https://example.com/thinking",
                    "content": "A book on cognitive biases by Daniel Kahneman.",
                    "score": 0.99
                },
                {
                    "title": "Nudge: The Final Edition",
                    "url": "https://example.com/nudge",
                    "content": "A book on choice architecture by Thaler and Sunstein.",
                    "score": 0.98
                }
            ]
        }
        # Configure the mock Tavily client instance to return the desired results
        mock_tavily_instance = mock_tavily_client.return_value
        mock_tavily_instance.search.return_value = mock_tavily_search_results

        # 3. Execute the function under test
        topic = "behavioral economics"
        books = search_google_books(topic)

        # 4. Assert the behavior
        # Verify Google Books API was called
        mock_requests_get.assert_called_once()

        # Verify Tavily was initialized and its search method was called
        mock_tavily_client.assert_called_once_with(api_key=unittest.mock.ANY)
        mock_tavily_instance.search.assert_called_once_with(query=f"best books on {topic}", search_depth="basic")

        # Verify the data is correctly adapted
        expected_output = [
            {'title': 'Thinking, Fast and Slow', 'authors': ['N/A'], 'description': 'A book on cognitive biases by Daniel Kahneman.'},
            {'title': 'Nudge: The Final Edition', 'authors': ['N/A'], 'description': 'A book on choice architecture by Thaler and Sunstein.'}
        ]
        self.assertEqual(books, expected_output)

    @patch('src.curator.TavilyClient')
    @patch('src.curator.requests.get')
    def test_google_books_api_exception_triggers_tavily_fallback(self, mock_requests_get, mock_tavily_client):
        # 1. Setup the failure condition for Google Books API
        mock_requests_get.side_effect = requests.exceptions.RequestException("Network Error")

        # 2. Setup the mock for the Tavily fallback
        mock_tavily_search_results = {
            "results": [
                {
                    "title": "Thinking, Fast and Slow",
                    "url": "https://example.com/thinking",
                    "content": "A book on cognitive biases by Daniel Kahneman.",
                    "score": 0.99
                }
            ]
        }
        mock_tavily_instance = mock_tavily_client.return_value
        mock_tavily_instance.search.return_value = mock_tavily_search_results

        # 3. Execute the function under test
        topic = "behavioral economics"
        books = search_google_books(topic)

        # 4. Assert the behavior
        mock_requests_get.assert_called_once()
        mock_tavily_client.assert_called_once_with(api_key=unittest.mock.ANY)
        mock_tavily_instance.search.assert_called_once_with(query=f"best books on {topic}", search_depth="basic")
        expected_output = [
            {'title': 'Thinking, Fast and Slow', 'authors': ['N/A'], 'description': 'A book on cognitive biases by Daniel Kahneman.'}
        ]
        self.assertEqual(books, expected_output)

if __name__ == '__main__':
    unittest.main()
