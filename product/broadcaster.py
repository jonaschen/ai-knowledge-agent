import os
import json
import re
from dotenv import load_dotenv
from google.cloud import texttospeech_v1beta1 as tts
from typing import List
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# 設定輸出檔案
OUTPUT_FILE = "output_podcast.mp3"
PROJECT_ID = os.getenv("PROJECT_ID", "project-391688be-0f68-469e-813")
LOCATION = os.getenv("LOCATION", "us-central1")

def generate_podcast_script(technical_doc: str):
    """
    (這部分邏輯保持不變，負責生成 JSON 劇本)
    """
    print("--- 正在生成 Podcast 劇本 (Broadcaster Agent) ---")
    
    llm = ChatVertexAI(
        model_name="gemini-2.0-flash-exp",
        project=PROJECT_ID,
        location=LOCATION,
        temperature=0.6, # 稍微調高，讓對話更自然
        model_kwargs={"response_mime_type": "application/json"}
    )

    prompt = """
    你是一檔高人氣技術 Podcast 的製作人。請將輸入的「技術架構文檔」改寫成一段 **極具張力** 的雙人對話腳本。
    
    【角色人設嚴格執行】
    1. **Alex (Host A)**: 
       - 背景：資深後端工程師，懷疑論者 (Skeptic)，討厭 Buzzwords。
       - 風格：講話酸溜溜，喜歡挑戰權威。
       - 任務：負責攻擊文檔中的漏洞。
    
    2. **Sarah (Host B)**: 
       - 背景：前 Google 架構師，現任 CTO。
       - 風格：權威、冷靜，擅長用系統設計 (System Design) 的視角解釋一切。
       - 任務：用具體的工程邏輯反擊 Alex。

    【劇本要求】
    1. 這是「辯論」，不是唸稿。要有來有往。
    2. 必須保留 Kubernetes, WORM, Event Sourcing 等硬核術語。
    3. 長度：約 8-12 個回合。

    【輸出格式】
    Strict JSON List:
    [
        {"speaker": "Alex", "text": "Wait, did you just say WORM storage? Is this 1990?"},
        {"speaker": "Sarah", "text": "In a compliance context, WORM is actually the most advanced pattern we have."}
    ]
    """
    
    try:
        response = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"技術文檔內容：\n{technical_doc}")
        ])
        
        # 嘗試解析 JSON
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', response.content, re.DOTALL)
            if match:
                return json.loads(match.group())
            else:
                raise ValueError("JSON 解析失敗")

    except Exception as e:
        print(f"❌ 劇本生成失敗: {e}")
        return []

def synthesize_audio(script: List[dict]):
    """
    [重構版] 分段合成策略 (Segment & Stitch)
    解決 Chirp 3 在長 SSML 中產生幻覺的問題。
    """
    if not script:
        print("❌ 錯誤: 劇本為空。")
        return

    print(f"--- 正在合成語音 (Segment & Stitch Mode) - 共 {len(script)} 個片段 ---")
    
    client = tts.TextToSpeechClient()
    audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3)
    
    # 用來暫存所有音頻片段的二進位數據
    combined_audio = b""

    for i, line in enumerate(script):
        text = line.get("text", "")
        speaker = line.get("speaker", "Sarah")
        
        # 簡單的進度條
        print(f"  -> Processing segment {i+1}/{len(script)}: [{speaker}] {text[:30]}...")

        # 1. 選擇聲音
        if speaker == "Alex":
            voice_name = "en-US-Chirp3-HD-Fenrir"
        else:
            voice_name = "en-US-Chirp3-HD-Leda"

        voice_params = tts.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name
        )

        # 2. 構建單句的輸入 (不使用複雜的 SSML，只用純文字以確保穩定)
        # 如果需要停頓，可以在文字後加一點標點
        input_text = tts.SynthesisInput(text=text)

        # 3. 調用 API
        try:
            response = client.synthesize_speech(
                request={
                    "input": input_text, 
                    "voice": voice_params, 
                    "audio_config": audio_config
                }
            )
            
            # 4. 拼接音頻 (MP3 格式可以直接二進位拼接)
            combined_audio += response.audio_content
            
            # (可選) 在兩句話之間插入一點靜音，這裡暫時省略，直接拼接聽起來節奏比較緊湊
            
        except Exception as e:
            print(f"  ⚠️ 片段 {i+1} 合成失敗: {e}")

    # 5. 一次性寫入檔案
    if combined_audio:
        with open(OUTPUT_FILE, "wb") as out:
            out.write(combined_audio)
        print(f"✅ 完整 Podcast 已生成: {OUTPUT_FILE} (大小: {len(combined_audio)/1024:.2f} KB)")
    else:
        print("❌ 生成失敗，音頻為空。")

# 測試用
if __name__ == "__main__":
    # 測試腳本
    dummy_script = [
        {"speaker": "Alex", "text": "Wait, why are we refactoring the broadcaster?"},
        {"speaker": "Sarah", "text": "Because the previous model was hallucinating alien languages due to SSML overload."}
    ]
    synthesize_audio(dummy_script)
