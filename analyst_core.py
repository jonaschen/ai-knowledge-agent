import os
import json
from typing import TypedDict, Literal
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import SystemMessage, HumanMessage

load_dotenv()

# --- 1. 配置與模型 ---
PROJECT_ID = os.getenv("PROJECT_ID", "project-391688be-0f68-469e-813")
LOCATION = os.getenv("LOCATION", "us-central1")

# 使用具備思考能力的 2.5 Pro
llm = ChatVertexAI(
    model_name="gemini-2.5-pro",
    project=PROJECT_ID,
    location=LOCATION,
    temperature=0.2,
    max_output_tokens=8192
)

# --- 2. 狀態定義 ---
class AnalysisState(TypedDict):
    original_text: str
    book_type: Literal["instructional", "narrative"] # 新增狀態：書籍類型
    draft_analysis: str
    critique_feedback: str
    revision_count: int

# --- 3. 多樣化 Prompts (Polymorphic Prompts) ---

# 路由 Prompt：判斷書籍類型
ROUTER_PROMPT = """
你是一個圖書分類專家。請分析以下文本片段，判斷這本書屬於哪種類型。

1. **Instructional**: 教學指南、手冊、方法論 (e.g., "How to run", "Sales Playbook").
2. **Narrative**: 歷史事件、傳記、小說、案例研究 (e.g., "History of Boston Marathon", "Steve Jobs Bio").

只回傳一個單字: "instructional" 或 "narrative"。
"""

# 策略 A: 針對工具書 (原本的邏輯)
INSTRUCTIONAL_PROMPT = """
你是一位資深架構師。輸入是一本「方法論指南」。
請將其**直接映射**為分佈式系統術語。
例如：
- "跑步訓練計畫" -> "系統壓力測試計畫 (Load Testing Schedule)"
- "休息日" -> "維護窗口 (Maintenance Window)"
- "心率區間" -> "資源利用率閾值 (Resource Utilization Thresholds)"

輸出格式：技術架構文檔 (Design Doc)。
"""

# 策略 B: 針對敘事/歷史書 (新增的邏輯 - 解決地獄梗問題)
NARRATIVE_PROMPT = """
你是一位資深架構師。輸入是一段「歷史敘事」或「傳記」。
**警告：不要將故事中的悲劇或災難直接映射為技術攻擊。這很不恰當。**

你的任務是進行 **Root Cause Analysis (RCA)**：
1. **抽象化**：從故事中提取「決策模式」、「組織失誤」或「危機處理原則」。
2. **架構化**：將這些「原則」應用於軟體工程。

例如：
- 如果故事是關於「馬拉松爆炸案後的混亂」-> 轉譯為「缺乏災難復原 (DR) 計劃與事件響應 (Incident Response) 流程的缺失」。
- 如果故事是關於「耐吉創辦人的資金斷裂」-> 轉譯為「系統資源枯竭 (Resource Exhaustion) 與流控失敗」。

輸出格式：事後檢討報告 (Post-Mortem Analysis) 或 系統韌性架構建議書。
"""

CRITIC_PROMPT = """
你是 Linus Torvalds 風格的審查員。
審查這份將商業/歷史內容轉化為工程系統的文檔。
確保：
1. 隱喻準確且不過度解讀。
2. **特別檢查**：如果原文是歷史災難，轉譯後的文檔是否保持了專業性，沒有將受害者變成數據包？
3. 是否去除了廢話？

如果通過，回覆 "LGTM"。否則列出修改建議。
"""

# --- 4. 節點函數 ---

def router_node(state: AnalysisState):
    """分類節點：決定走哪條路"""
    print("--- [Router] 正在分析書籍類型 ---")
    response = llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(content=state['original_text'][:2000]) # 只看前 2000 字判斷即可
    ])
    
    book_type = response.content.strip().lower()
    # 簡單的清理，防止 LLM 多話
    if "narrative" in book_type:
        decision = "narrative"
    else:
        decision = "instructional"
        
    print(f"-> 判定類型: {decision.upper()}")
    return {"book_type": decision}

def draft_node(state: AnalysisState):
    book_type = state["book_type"]
    print(f"--- [Phase 1] 生成初稿 (Strategy: {book_type}) ---")
    
    # 根據類型選擇 Prompt
    if book_type == "narrative":
        sys_msg = NARRATIVE_PROMPT
    else:
        sys_msg = INSTRUCTIONAL_PROMPT
        
    response = llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=f"原始文本：\n{state['original_text']}")
    ])
    
    return {"draft_analysis": response.content, "revision_count": 1}

def critique_node(state: AnalysisState):
    print(f"--- [Phase 2] 代碼審查 (Review Round {state.get('revision_count')}) ---")
    response = llm.invoke([
        SystemMessage(content=CRITIC_PROMPT),
        HumanMessage(content=f"待審查文檔：\n{state['draft_analysis']}")
    ])
    return {"critique_feedback": response.content}

def revise_node(state: AnalysisState):
    print("--- [Phase 3] 重構中 (Refactoring) ---")
    # 這裡也要根據類型選擇 Prompt 來保持一致性
    book_type = state["book_type"]
    sys_msg = NARRATIVE_PROMPT if book_type == "narrative" else INSTRUCTIONAL_PROMPT
    
    prompt = f"""
    請根據 Review 意見重寫分析。
    Review 意見：{state['critique_feedback']}
    原草稿：{state['draft_analysis']}
    """
    response = llm.invoke([
        SystemMessage(content=sys_msg),
        HumanMessage(content=prompt)
    ])
    return {"draft_analysis": response.content, "revision_count": state.get("revision_count", 1) + 1}

# --- 5. 圖構建 ---

def should_continue(state: AnalysisState):
    feedback = state['critique_feedback']
    count = state['revision_count']
    
    if "LGTM" in feedback:
        print("--- Review 通過 (LGTM) ---")
        return END
    if count >= 3:
        print("--- Max Retries Hit ---")
        return END
    return "revise"

workflow = StateGraph(AnalysisState)

# 新增 Router 節點
workflow.add_node("router", router_node)
workflow.add_node("draft", draft_node)
workflow.add_node("critique", critique_node)
workflow.add_node("revise", revise_node)

# 設定流程：Start -> Router -> Draft ...
workflow.set_entry_point("router")
workflow.add_edge("router", "draft")
workflow.add_edge("draft", "critique")
workflow.add_conditional_edges(
    "critique",
    should_continue,
    {"revise": "revise", END: END}
)
workflow.add_edge("revise", "critique")

app = workflow.compile()
