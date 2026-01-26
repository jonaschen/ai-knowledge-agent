
import unittest
from unittest.mock import patch, MagicMock
from googleapiclient.errors import HttpError
import io
import os


from product.curator import Curator

class TestCuratorIntegration(unittest.TestCase):

    @patch('product.curator.Curator._search_google_books')
    @patch('product.curator.Researcher')
    def test_curator_uses_researcher_on_google_429_error(self, mock_researcher_class, mock_search_google_books):
        """
        Given: The Google Books API returns a 429 Rate Limit error.
        When: The Curator searches for a book.
        Then: It should use the Researcher agent as a fallback.
        And: It should adapt the Researcher's output to the expected format.
        """
        # --- Arrange ---
        # 1. Mock the Google Books API to raise a 429 error
        mock_search_google_books.side_effect = HttpError(
            resp=MagicMock(status=429, reason="Rate Limit Exceeded"),
            content=b'Rate Limit Exceeded'
        )

        # 2. Mock the Researcher to return a specific book list
        mock_researcher_instance = MagicMock()
        mock_researcher_instance.find_books.return_value = [
            {
                "title": "Researched Book Title",
                "authors": ["Author One", "Author Two"],
                "content": "A description from the researcher.",
                "source": "researcher_fallback" # Add a field to prove origin
            }
        ]
        mock_researcher_class.return_value = mock_researcher_instance

        # --- Act ---
        curator = Curator()
        topic = "A Fictional Topic"
        result = curator.search(topic)

        # --- Assert ---
        # 1. Verify Researcher was called
        mock_researcher_class.assert_called_once()
        mock_researcher_instance.find_books.assert_called_once_with(topic)

        # 2. Verify the output is the adapted data from the Researcher
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], "Researched Book Title")
        self.assertEqual(result[0]['authors'], ["Author One", "Author Two"])
        self.assertEqual(result[0]['description'], "A description from the researcher.")
