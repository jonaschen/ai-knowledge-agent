import logging
import requests
import json
import os
import re
from typing import TypedDict, List, Optional
from dotenv import load_dotenv
from tavily import TavilyClient
from langgraph.graph import StateGraph, END
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

load_dotenv()

# --- 0. 配置 LLM ---
PROJECT_ID = os.getenv("PROJECT_ID", "project-391688be-0f68-469e-813")
LOCATION = os.getenv("LOCATION", "us-central1")

llm = ChatVertexAI(
    model_name="gemini-2.5-pro",
    project=PROJECT_ID,
    location=LOCATION,
    temperature=0.1,
    max_output_tokens=1024
)

class Curator:
    def __init__(self):
        self.tavily_api_key = os.getenv("TAVILY_API_KEY")

    def _adapt_tavily_results(self, results: dict) -> list:
        """Adapts Tavily search results to our standard book format."""
        adapted_books = []
        if "results" in results:
            for item in results["results"]:
                adapted_books.append({
                    "title": item.get("title"),
                    "authors": ["N/A"],
                    "description": item.get("content"),
                })
        return adapted_books

    def _fallback_to_tavily(self, query: str) -> list:
        """Initializes Tavily client, performs search, and adapts results."""
        client = TavilyClient(api_key=self.tavily_api_key)
        tavily_results = client.search(query=f"best books on {query}", search_depth="basic")
        return self._adapt_tavily_results(tavily_results)

    def _search_google_books(self, query: str, max_results=20):
        """從 Google Books 獲取候選書籍"""
        print(f"--- 正在搜索 Google Books: {query} ---")
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {
            "q": query,
            "langRestrict": "en", # 英文書通常技術含量較高
            "orderBy": "relevance",
            "maxResults": max_results
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        resp = requests.get(url, params=params, headers=headers)
        resp.raise_for_status() # Will raise an HTTPError for bad responses (4xx or 5xx)

        data = resp.json()

        books = []
        if "items" in data:
            for item in data["items"]:
                info = item.get("volumeInfo", {})
                books.append({
                    "title": info.get("title"),
                    "authors": info.get("authors", []),
                    "publisher": info.get("publisher", "Unknown Publisher"),
                    "publishedDate": info.get("publishedDate", "Unknown Date"),
                    "description": info.get("description", ""),
                    "rating": info.get("averageRating", 0),
                    "ratingsCount": info.get("ratingsCount", 0)
                })
        else:
            logging.warning(f"Google Books API Response (No items): {data}")
        return books

    def search(self, query: str):
        """
        Searches for a book, first using Google Books and falling back to Tavily.
        """
        try:
            print("Attempting search with primary API (Google Books)...")
            return self._search_google_books(query)
        except Exception as e:
            print(f"Primary API failed: {e}. Falling back to Tavily.")
            return self._fallback_to_tavily(query)


# --- 1. 定義狀態 ---
class CuratorState(TypedDict):
    topic: str                  # 用戶想學的主題 (e.g., "B2B Sales")
    raw_candidates: List[dict]  # Google Books 找到的書
    vetted_books: List[dict]    # 經過 Reliability 驗證的書
    selected_book: dict         # 最終選定的一本書


def verify_source_reliability(book: dict) -> dict:
    """
    使用 LLM 驗證書籍的可靠性 (Reliability Verification)
    替代原本的 Hacker News Score
    """
    print(f"--- Verifying Reliability: {book.get('title', 'Unknown Title')} ---")

    try:
        # Handle empty description to prevent "Empty External Insights" 400 error
        description = book.get('description', "")
        if not description or not description.strip():
            description = "No description available. Please judge based on Title, Author, and Publisher."

        # Format authors nicely
        authors = book.get('authors', [])
        if isinstance(authors, list):
            authors_str = ", ".join(authors)
        else:
            authors_str = str(authors)

        prompt = f"""
    You are a strictly critical librarian and technical book curator.
    Evaluate the reliability and credibility of the following book for a professional audience.

    Title: {book.get('title', 'Unknown Title')}
    Author: {authors_str}
    Publisher: {book.get('publisher', 'Unknown Publisher')}
    Date: {book.get('publishedDate', 'Unknown Date')}
    Description: {description}

    Criteria:
    1. **Author Authority**: Is the author a known expert or practitioner in the field?
    2. **Publisher Reputation**: Is the publisher reputable for technical/business books (e.g., O'Reilly, Pearson, Wiley, Harvard Business Review) vs self-published/unknown?
    3. **Content Depth**: Does the description suggest deep, actionable insights or superficial fluff?

    Score the book from 0 to 10 (10 being highest reliability/quality).
    Provide a brief reason.

    Return ONLY a JSON object:
    {{
        "score": 8.5,
        "reason": "Reputable publisher (O'Reilly) and author is a known expert."
    }}
    """

        response = llm.invoke([
            HumanMessage(content=prompt)
        ])
        content = response.content.strip()

        # Robust JSON extraction with regex
        try:
            # Regex to find a JSON object within a larger string
            match = re.search(r'\{.*\}', content, re.DOTALL)

            if match:
                json_string = match.group(0)
            else:
                # Fallback to the original string if no JSON object is found
                json_string = content

            result = json.loads(json_string)

        except json.JSONDecodeError:
            print(f"JSON Parsing Failed. Content: {content[:100]}...")
            return {"score": 5.0, "reason": "JSON parsing failed, using default score."}

        # Defensive coding: Ensure keys exist
        score = result.get('score', 5.0)
        reason = result.get('reason', "No reason provided.")

        print(f"  -> Reliability Score: {score} ({reason})")
        return {"score": score, "reason": reason}
    except Exception as e:
        print(f"Reliability Verification Error: {e}")
        return {"score": 5.0, "reason": "Verification failed, using default score."}

# --- 3. 節點邏輯 ---

def search_node(state: CuratorState):
    topic = state["topic"]
    # 優化：只在主題看起來很寬泛時才加後綴，或者讓 LLM 決定關鍵字 (這裡先簡化處理)
    if "startup" in topic.lower() or "business" in topic.lower():
        query = topic
    else:
        # 稍微放寬，改用 "concept book" 來找書，而不是硬推 startup
        query = f"{topic} book" 
    
    print(f"--- 調整後的搜尋 Query: {query} ---")
    curator = Curator()
    candidates = curator.search(query)
    return {"raw_candidates": candidates}

def validation_node(state: CuratorState):
    candidates = state["raw_candidates"]
    vetted = []
    
    print("--- 正在進行 Reliability Verification ---")
    for book in candidates:
        g_rating = book.get("rating", 0) or 0
        
        # Reliability Check
        reliability = verify_source_reliability(book)
        r_score = reliability["score"]
        
        # Final Score Formula:
        # We prioritize Reliability.
        # Final Score = (Reliability * 0.7) + (GoogleRating * 2 * 0.3) -> both normalized to approx 0-10 scale
        
        final_score = (r_score * 0.7) + (g_rating * 2 * 0.3)
        
        book_data = {
            **book,
            "reliability_score": r_score,
            "reliability_reason": reliability["reason"],
            "final_score": final_score
        }
        
        # Filter threshold: Reliability must be > 6.0
        if r_score >= 6.0:
            vetted.append(book_data)

    # Sort
    vetted.sort(key=lambda x: x["final_score"], reverse=True)
    
    best_book = vetted[0] if vetted else None
    
    if best_book:
        print(f"--- 最終選書: 《{best_book['title']}》 (Score: {best_book['final_score']:.1f}) ---")

    return {"vetted_books": vetted, "selected_book": best_book}

# --- 4. 構建圖 ---
workflow = StateGraph(CuratorState)

workflow.add_node("search", search_node)
workflow.add_node("validate", validation_node)

workflow.set_entry_point("search")
workflow.add_edge("search", "validate")
workflow.add_edge("validate", END)

app = workflow.compile()

# --- 5. 測試 ---
if __name__ == "__main__":
    # 測試題目
    input_topic = "B2B Sales"
    
    print(f"Topic: {input_topic}")
    print("="*50)
    
    result = app.invoke({"topic": input_topic})
    
    print("="*50)
    if result["selected_book"]:
        book = result["selected_book"]
        print(f"Title: {book['title']}")
        print(f"Author: {book['authors']}")
        print(f"Description: {book['description'][:100]}...")
        print(f"Reliability Score: {book['reliability_score']}")
        print(f"Reason: {book.get('reliability_reason')}")
    else:
        print("未找到合適的書籍。")
