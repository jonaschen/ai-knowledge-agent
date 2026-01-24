from tavily import TavilyClient

class Researcher:
    """
    An agent responsible for fetching external validation and sources
    using the Tavily search API.
    """
    def __init__(self, tavily_api_key: str):
        """
        Initializes the Researcher with a Tavily API key.

        Args:
            tavily_api_key (str): The API key for the Tavily service.
        """
        if not tavily_api_key:
            raise ValueError("TAVILY_API_KEY cannot be empty.")
        self.client = TavilyClient(api_key=tavily_api_key)

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        """
        Performs a search using the Tavily API and returns structured results.

        Args:
            query (str): The search query.
            max_results (int): The maximum number of results to return.

        Returns:
            list[dict]: A list of search results, each a dictionary with
                        'title', 'url', and 'content'.
        """
        try:
            response = self.client.search(query=query, search_depth="basic", max_results=max_results)
            results = response.get('results', [])
            # Filter out low-quality sources (e.g., social media)
            filtered_results = [result for result in results if "twitter.com" not in result.get('url', '')]
            return filtered_results
        except Exception as e:
            # In a real-world scenario, we'd have more robust logging.
            print(f"An error occurred during search: {e}")
            return []

    def get_book_reviews(self, book_title: str) -> list[dict]:
        """
        A specialized search method to find reviews for a specific book.

        Args:
            book_title (str): The title of the book to find reviews for.

        Returns:
            list[dict]: A list of search results from the main search method.
        """
        # Construct a query tailored for finding book reviews.
        query = f'reviews of the book "{book_title}"'
        return self.search(query=query)
