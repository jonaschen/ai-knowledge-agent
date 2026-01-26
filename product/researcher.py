import os
import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Optional
from tavily import TavilyClient

load_dotenv()

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

    def find_books(self, topic: str) -> list[dict]:
        """
        A specialized search method to find books on a specific topic.

        Args:
            topic (str): The topic to find books about.

        Returns:
            list[dict]: A list of search results from the main search method.
        """
        # Construct a query tailored for finding books.
        query = f'books on the topic of "{topic}"'
        return self.search(query=query)


# --- Additional Content Fetching Utilities (Youtube, HN) ---

# 請將你剛剛建立的 API Key 填入這裡
# 注意：真實專案中應該用環境變數 os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_hn_comments(book_title: str) -> str:
    """
    [新增功能] 抓取 Hacker News 上關於這本書的高質量評論
    這是解決「內容空洞」的關鍵補丁。
    """
    print(f"--- 正在挖掘 Hacker News 評論: '{book_title}' ---")

    # 1. 搜尋討論串 ID
    search_url = "http://hn.algolia.com/api/v1/search"
    params = {
        "query": book_title,
        "tags": "story",
        "numericFilters": "points>50" # 只看有熱度的
    }

    try:
        resp = requests.get(search_url, params=params).json()
        if not resp["hits"]:
            return ""

        # 取最高分的那個討論串
        best_story = resp["hits"][0]
        story_id = best_story["objectID"]

        # 2. 抓取該討論串的詳細評論
        item_url = f"http://hn.algolia.com/api/v1/items/{story_id}"
        item_resp = requests.get(item_url).json()

        comments_text = []

        def extract_comments(node, depth=0):
            # 限制遞迴深度與數量，避免 Context 爆炸，但 Gemini 2.5 Pro 吃得下
            if depth > 3: return

            if node.get("text"):
                # 清洗 HTML tag
                import re
                clean_text = re.sub('<[^<]+?>', '', node["text"])
                # 加上標記，讓 LLM 知道這是工程師的評論
                comments_text.append(f"[Engineer Comment]: {clean_text}")

            for child in node.get("children", []):
                extract_comments(child, depth + 1)

        extract_comments(item_resp)

        # 合併成一個大字串
        full_comments = "\n".join(comments_text[:30]) # 取前 30 條精華
        print(f"-> ✅ 成功抓取 {len(comments_text[:30])} 條工程師評論")
        return full_comments

    except Exception as e:
        print(f"⚠️ HN 評論抓取失敗: {e}")
        return ""

def search_author_interview(book_title: str, authors: list) -> Optional[str]:
    """
    搜尋作者關於這本書的訪談影片
    返回: Video ID
    """
    if not YOUTUBE_API_KEY:
        print("錯誤: 請設定 YOUTUBE_API_KEY")
        return None

    author_name = authors[0] if authors else "Author"
    query = f"{book_title} {author_name} interview podcast"

    print(f"--- 正在 YouTube 搜尋: '{query}' ---")

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    # 搜尋長度超過 20 分鐘的影片 (確保是深度訪談)
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        videoDuration="long", # > 20 mins
        maxResults=1
    )
    response = request.execute()

    if not response["items"]:
        print("未找到相關訪談。")
        return None

    video_id = response["items"][0]["id"]["videoId"]
    video_title = response["items"][0]["snippet"]["title"]
    print(f"-> 找到影片: {video_title} (ID: {video_id})")

    return video_id

def get_transcript_text(video_id: str) -> str:
    """下載並合併字幕"""
    print(f"--- 正在下載字幕 (ID: {video_id}) ---")
    try:
        # 優先嘗試自動生成的英文字幕
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US'])

        # 將碎片化的字幕拼成全文
        full_text = " ".join([t['text'] for t in transcript_list])

        # 簡單的清理
        full_text = full_text.replace("\n", " ")
        print(f"-> 字幕獲取成功 (長度: {len(full_text)} 字rs)")
        return full_text

    except Exception as e:
        print(f"字幕下載失敗: {e}")
        # 備案：如果是因為沒有字幕，這裡可以接 Whisper API 來轉錄 (但在本專案先略過)
        return ""
