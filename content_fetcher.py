import os
import requests
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Optional

load_dotenv()

# 請將你剛剛建立的 API Key 填入這裡
# 注意：真實專案中應該用環境變數 os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyDKh34tVT_qwlWfXCaZUIyHJyKEnBZwrmc")

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

# 測試用
if __name__ == "__main__":
    # 測試我們剛剛選出的書
    test_book = "Fast Forward: Accelerating B2B Sales for Startups"
    test_author = ["Matthias Hilpert"] # 假設的作者
    
    vid = search_author_interview(test_book, test_author)
    if vid:
        text = get_transcript_text(vid)
        print(f"預覽內容: {text[:200]}...")
