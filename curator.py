import requests
import json
import os
from typing import TypedDict, List, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage
from content_fetcher import get_hn_comments

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

# --- 1. 定義狀態 ---
class CuratorState(TypedDict):
    topic: str                  # 用戶想學的主題 (e.g., "B2B Sales")
    raw_candidates: List[dict]  # Google Books 找到的書
    vetted_books: List[dict]    # 經過 HN 驗證的書
    selected_book: dict         # 最終選定的一本書

# --- 2. 工具函數 (API Clients) ---

def search_google_books(query: str, max_results=20):
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
    try:
        resp = requests.get(url, params=params, headers=headers)
        data = resp.json()

        books = []
        if "items" in data:
            for item in data["items"]:
                info = item.get("volumeInfo", {})
                books.append({
                    "title": info.get("title"),
                    "authors": info.get("authors", []),
                    "description": info.get("description", ""),
                    "rating": info.get("averageRating", 0),
                    "ratingsCount": info.get("ratingsCount", 0)
                })
        return books
    except Exception as e:
        print(f"Google Books API Error: {e}")
        return []

def get_hn_sentiment(book_title: str):
    """
    從 Hacker News (Algolia) 獲取工程師評價
    報告中提到的 'Engineer-Fit Algorithm' 的簡化版 [cite: 53]
    """
    url = "http://hn.algolia.com/api/v1/search"
    # 搜索這本書的討論串
    params = {
        "query": book_title,
        "tags": "story",
        "numericFilters": "points>20" # 只看有點熱度的討論
    }
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        
        hits = data.get("hits", [])
        if not hits:
            return {"score": 0, "comments_count": 0, "top_comment": ""}
            
        # 計算熱度 (簡單累加 points)
        total_points = sum(hit.get("points", 0) for hit in hits)
        total_comments = sum(hit.get("num_comments", 0) for hit in hits)
        
        print(f"  -> Found HN discussions for '{book_title}': {total_points} points")
        
        return {
            "score": total_points,
            "comments_count": total_comments,
            "top_discussion_id": hits[0].get("objectID") if hits else None
        }
    except Exception as e:
        print(f"HN API Error: {e}")
        return {"score": 0}

def analyze_sentiment(comments_text: str) -> dict:
    """使用 LLM 分析評論情感"""
    if not comments_text:
        return {"score": 0.0, "summary": "No comments available."}

    print("  -> Analyzing sentiment of comments...")
    prompt = """
    You are a sentiment analyzer for Hacker News comments.
    Analyze the following comments about a book.
    Determine the overall sentiment score from -1.0 (very negative) to 1.0 (very positive).
    Also provide a brief summary of the engineers' opinions (max 2 sentences).

    Return ONLY a JSON object:
    {
        "score": 0.5,
        "summary": "Engineers found the book practical but outdated."
    }
    """

    try:
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=comments_text[:5000]) # Limit context to avoid overflow/cost
        ])
        content = response.content.strip()
        # Clean up code blocks if present
        if content.startswith("```json"):
            content = content[7:-3]
        elif content.startswith("```"):
            content = content[3:-3]

        return json.loads(content)
    except Exception as e:
        print(f"Sentiment Analysis Error: {e}")
        return {"score": 0.0, "summary": "Analysis failed."}

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
    candidates = search_google_books(query)
    return {"raw_candidates": candidates}

def validation_node(state: CuratorState):
    candidates = state["raw_candidates"]
    topic = state["topic"]
    vetted = []
    
    print("--- 正在進行 Hacker News 信號驗證 ---")
    for book in candidates:
        g_rating = book.get("rating", 0) or 0
        g_count = book.get("ratingsCount", 0) or 0

        # [修正] 放寬條件：
        # 只過濾掉明確的爛書 (>0 但 <3.0)。
        # 允許 0/0 (無評分) 的書通過，因為它們可能是冷門佳作，稍後看 HN 反應。
        if g_rating > 0 and g_rating < 3.0:
            print(f"  -> Skipping '{book['title']}' (Low quality: {g_rating}/{g_count})")
            continue

        hn_data = get_hn_sentiment(book["title"])
        hn_score = hn_data["score"]
        
        # 優化：相關性懲罰 (Relevance Penalty)
        relevance_score = 1.0
        topic_words = set(topic.lower().split())
        title_words = set(book["title"].lower().split())
        
        # 計算交集
        common_words = topic_words.intersection(title_words)
        
        if len(common_words) > 0:
            relevance_score = 1.2
        else:
            desc_words = set(book.get("description", "").lower().split())
            if len(topic_words.intersection(desc_words)) > 0:
                relevance_score = 0.8
            else:
                relevance_score = 0.1
            
        # 正規化 HN 分數
        norm_hn = min(hn_score, 500) / 100  # 範圍約 0~5
        
        # 混合評分 (Google 評分權重 0.3, HN 權重 0.7)
        final_score = (norm_hn * 0.7) + (g_rating * 0.3)
        final_score *= relevance_score
        
        # 只要有任何信號 (Google 評分 > 0 或 HN 分數 > 0) 就保留，或者如果都為 0 但通過了過濾器，也暫時保留
        if final_score > 0 or g_rating >= 0:
            book_data = {
                **book,
                "hn_score": hn_score,
                "final_score": final_score,
                "hn_comments_count": hn_data["comments_count"]
            }
            vetted.append(book_data)
    
    # 根據初步評分排序
    vetted.sort(key=lambda x: x["final_score"], reverse=True)

    # --- Deep Dive: Sentiment Analysis for Top Candidates ---
    # 取前 5 名進行深度分析
    top_candidates = vetted[:5]
    print(f"--- 對前 {len(top_candidates)} 名候選書籍進行深度情感分析 ---")

    for book in top_candidates:
        # 獲取具體評論內容
        comments_text = get_hn_comments(book["title"])

        sentiment_data = {"score": 0.0, "summary": "No specific comments analyzed."}
        if comments_text:
             sentiment_data = analyze_sentiment(comments_text)

        book["sentiment_score"] = sentiment_data["score"]
        book["sentiment_summary"] = sentiment_data["summary"]

        # 根據情感分數調整最終得分
        # 如果情感分數是正的 (e.g., 0.8)，增加分數。如果是負的 (-0.5)，扣分。
        # 假設最大加權為 50%
        adjustment_factor = 1 + (book["sentiment_score"] * 0.5)

        old_score = book["final_score"]
        book["final_score"] = old_score * adjustment_factor

        print(f"  -> Book: {book['title']}")
        print(f"     Sentiment: {sentiment_data['score']} ({sentiment_data['summary']})")
        print(f"     Score Adjusted: {old_score:.2f} -> {book['final_score']:.2f}")

    # 重新排序
    vetted.sort(key=lambda x: x["final_score"], reverse=True)
    
    best_book = vetted[0] if vetted else None
    
    if best_book:
        print(f"--- 最終選書: 《{best_book['title']}》 (Final Score: {best_book['final_score']:.1f}) ---")
    
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
        print(f"Hacker News Score: {book['hn_score']}")
        print(f"Sentiment: {book.get('sentiment_summary')}")
    else:
        print("未找到合適的書籍。")
