# analyst.py (深度優化版)
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import json

def generate_script(book_title, book_description, project_id):
    """
    利用 Gemini 2.0 Flash/Pro 生成「深度」工程師視角 Podcast 腳本
    """
    print(f"正在深度解析書籍: {book_title}...")
    
    # 請根據您上一步的測試，確認使用可用的模型 (如 gemini-2.0-flash-exp)
    vertexai.init(project=project_id, location="us-central1") # 或 asia-northeast1
    
    # --- 核心升級：工程師思維轉譯 Prompt ---
    # 這裡實作了報告中提到的 "Isomorphic Mapping" (同構映射) 
    system_instruction = """
    你是一位擁有 20 年經驗的 Google Staff Engineer，現在轉型為技術創業家。
    你的任務不是「總結書籍」，而是將商業邏輯「重構 (Refactor)」為工程師聽得懂的系統架構。

    【角色設定】
    - Host A (Alex): 資深架構師，懷疑論者。他討厭商業術語 (Buzzwords)，認為那是 "Syntactic Sugar"。他只關心系統的 Scalability, Latency 和 Fault Tolerance。
    - Host B (Sarah): 技術出身的創辦人。她負責將商業概念翻譯成 Alex 能懂的技術隱喻。

    【深度分析規則 (必須遵守)】
    1. **調用內部知識**：請忽略輸入的簡短摘要，直接調用你關於這本書的完整閱讀記憶。
    2. **強制工程映射 (Engineering Mapping)**：
       - 講 "MVP" 時，不要說「最小可行性產品」，要說是「針對市場假設的單元測試 (Unit Test for Market Assumptions)」。
       - 講 "Pivot" 時，不要說「轉型」，要說是「Runtime Configuration Change (執行時配置變更)」。
       - 講 "Marketing" 時，要比喻為 "Traffic Acquisition & Filtering Pipeline (流量獲取與過濾管線)"。
    3. **拒絕淺層摘要**：不要列出章節標題。要討論「反直覺 (Counter-intuitive)」的觀點。
    4. **口語化**：使用台灣工程師的混雜語氣 (晶晶體)，例如：「這本質上就是個 O(n^2) 的解法，效率太差了」。

    【輸出格式】
    JSON 列表，包含 "speaker" ("A" 或 "B") 和 "text"。
    """
    
    # 使用我們剛測試成功的 Gemini 2.0 模型
    model = GenerativeModel(
        "gemini-2.0-flash-exp", 
        system_instruction=[system_instruction]
    )
    
    # 透過 Prompt 強制模型挖掘深度
    prompt = f"""
    目標書籍：{book_title}
    
    請為我生成一段 Podcast 腳本，重點討論這本書最核心的 3 個 Mental Models。
    
    情境：
    Alex 質疑這本書只是另一本商業雞湯，Sarah 必須用「系統設計」的角度來證明這本書的邏輯是嚴密的。
    
    請確保對話中包含具體的工程類比，例如將商業模式比喻為分散式系統的 CAP 定理權衡。
    """
    
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    try:
        script_json = json.loads(response.text)
        return script_json
    except json.JSONDecodeError:
        print("JSON 解析失敗，嘗試修復...")
        # 簡單的容錯處理
        cleaned_text = response.text.strip().removeprefix("```json").removesuffix("```")
        return json.loads(cleaned_text)

# ... (if __name__ == "__main__": 部分保持不變)
if __name__ == "__main__":
    # 測試用 (請換成您的 Project ID)
    PROJECT_ID = "ai-biz-learner" 
    sample_script = generate_script("The Lean Startup", "MVP is about validating learning.", PROJECT_ID)
    print(json.dumps(sample_script, indent=2, ensure_ascii=False))
