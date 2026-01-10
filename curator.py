import requests
import json
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END

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
    resp = requests.get(url, params=params)
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

# --- 3. 節點邏輯 ---

def search_node(state: CuratorState):
    topic = state["topic"]
    # 優化：只在主題看起來很寬泛時才加後綴，或者讓 LLM 決定關鍵字 (這裡先簡化處理)
    # 針對 "training plan" 這種詞，加 "startup" 反而會誤導
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
        # [Report Requirement] 實作報告中的質量閾值 
        g_rating = book.get("rating", 0) or 0
        g_count = book.get("ratingsCount", 0) or 0
        # [修正] 放寬條件：
        # 1. 如果有評分但很低 (< 3.0)，這是爛書 -> Skip
        # 2. 如果完全沒評分 (0/0)，可能是雜訊 -> Skip
        # 注意：Hal Higdon (5/1) 會通過這個檢查，因為 g_rating=5 >= 3.0
        if (g_rating > 0 and g_rating < 3.0) or (g_rating == 0 and g_count == 0):
            print(f"  -> Skipping '{book['title']}' (Low quality or no data: {g_rating}/{g_count})")
            continue
        ## 如果評分太低或樣本數太少，直接跳過 (除非它是全新書，這裡假設我們找經典)
        #if g_rating < 3.5 or g_count < 10: 
        #    print(f"  -> Skipping '{book['title']}' (Low ratings: {g_rating}/{g_count})")
        #    continue

        hn_data = get_hn_sentiment(book["title"])
        hn_score = hn_data["score"]
        
        # 優化：相關性懲罰 (Relevance Penalty)
        # 如果書名跟主題完全沒關係，就算分數高也要扣分
        # (這裡用簡單的字串比對示範，理想情況是用 Embedding 算相似度)
        relevance_score = 1.0
        topic_words = set(topic.lower().split())
        title_words = set(book["title"].lower().split())
        
        # 計算交集 (Intersection)
        common_words = topic_words.intersection(title_words)
        
        if len(common_words) > 0:
            relevance_score = 1.2
        else:
            # 沒直接命中，但也許在描述(Description)裡？
            desc_words = set(book.get("description", "").lower().split())
            if len(topic_words.intersection(desc_words)) > 0:
                relevance_score = 0.8 # 稍微扣一點分但不要懲罰太重
            else:
                relevance_score = 0.1 # 重罰：標題和描述都不相關
            
        # 正規化 HN 分數 (假設 500 分是滿分，避免數值過大)
        norm_hn = min(hn_score, 500) / 100  # 範圍約 0~5
        
        # 混合評分 (權重參考報告 ，稍微調整適應現狀)
        # HN 權重 0.7 (工程師認可最重要), Google 評分權重 0.3
        final_score = (norm_hn * 0.7) + (g_rating * 0.3)
        
        # 最後乘上相關性係數
        final_score *= relevance_score
        #final_score = hn_score * relevance_score
        
        if final_score > 0: # 只保留有分數的
            book_data = {
                **book,
                "hn_score": hn_score,
                "final_score": final_score, # 用這個來排序
                "hn_comments": hn_data["comments_count"]
            }
            vetted.append(book_data)
    
    # 改用 final_score 排序
    vetted.sort(key=lambda x: x["final_score"], reverse=True)
    
    best_book = vetted[0] if vetted else None
    
    if best_book:
        print(f"--- 最終選書: 《{best_book['title']}》 (Adj Score: {best_book['final_score']:.1f}) ---")
    
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
    # 測試題目：B2B 銷售 (工程師最頭痛的領域)
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
    else:
        print("未找到合適的書籍。")
