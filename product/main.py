import sys
import os

# 導入我們寫好的模組
from product.curator import app as curator_app
from product.researcher import search_author_interview, get_transcript_text, get_hn_comments
from product.analyst_core import app as analyst_app
from product.broadcaster import generate_podcast_script, synthesize_audio

def run(topic: str):
    """
    Runs the full product pipeline for a given topic.
    """
    user_topic = topic
        
    print(f"🔥 啟動學習系統，目標主題: {user_topic}")
    print("="*60)
    
    # --- Phase 1: Curator (選書) ---
    print("\n[Step 1] 啟動 Curator Agent...")
    curator_result = curator_app.invoke({"topic": user_topic})
    selected_book = curator_result.get("selected_book")
    
    if not selected_book:
        print("❌ 選書失敗，流程終止。")
        return

    print(f"✅ 鎖定書籍: 《{selected_book['title']}》")
    
    # --- Phase 2: Content Fetcher (獲取數據) ---
    print("\n[Step 2] 聚合多維度數據 (YouTube + Hacker News)...")
    # 1. 嘗試 YouTube
    video_id = search_author_interview(selected_book['title'], selected_book['authors'])
    youtube_text = ""
    if video_id:
        youtube_text = get_transcript_text(video_id)
        
    # 2. 嘗試 Hacker News 評論 (新功能)
    hn_comments = get_hn_comments(selected_book['title'])
    
    # 3. 數據融合 (Context Fusion)
    raw_text = f"""
    Book Title: {selected_book['title']}
    Description: {selected_book['description']}
    
    --- YouTube Interview Transcript ---
    {youtube_text if youtube_text else "No interview available."}
    
    --- Hacker News Engineer Discussions ---
    {hn_comments if hn_comments else "No discussions available."}
    """
    
    # 4. (關鍵) 如果真的什麼都沒有，啟用「內在知識喚醒」
    if not youtube_text and not hn_comments:
        print("⚠️ 外部數據源枯竭。啟用 Gemini 內在參數化記憶...")
        raw_text += "\n[System Instruction]: External data is missing. Please use your internal training knowledge about this book to perform the analysis."


    # --- Phase 3: Analyst (思維轉譯) ---
    print(f"\n[Step 3] 啟動 Analyst Agent (Gemini 2.5 Pro)...")
    print("正在將商業內容編譯為工程架構文檔...")
    
    # 這裡我們傳入從 YouTube 抓到的字幕
    analyst_result = analyst_app.invoke({
        "original_text": raw_text, 
        "revision_count": 0
    })
    
    print("="*60)
    print("🚀 [編譯完成] 工程師專屬學習文檔：")
    print("="*60)
    print(analyst_result["draft_analysis"])

# ... (接在 Analyst 輸出之後)

    # --- Phase 4: Broadcaster (語音合成) ---
    print(f"\n[Step 4] 啟動 Broadcaster Agent...")
    
    # 1. 生成劇本
    script = generate_podcast_script(analyst_result["draft_analysis"])
    
    # 2. 合成語音
    synthesize_audio(script)
    
    print("\n🎉 系統執行完畢！請打開 output_podcast.mp3 收聽你的學習成果。")


def main():
    # 1. 設定目標
    user_topic = "B2B Sales for Startups"
    if len(sys.argv) > 1:
        user_topic = sys.argv[1]
    run(user_topic)


if __name__ == "__main__":
    main()
