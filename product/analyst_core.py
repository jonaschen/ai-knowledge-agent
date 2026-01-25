"""
Analyst Core Module
-------------------
Implements the Analyst Agent using a Reflexion Loop pattern via LangGraph.
Flow: Router -> Draft -> Critique -> Revise -> Critique -> ... -> End
"""
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
MAX_RETRIES = 3

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

# --- Thematic Tree Prompts ---
THESIS_PROMPT = """
Based on the following text, what is the single central thesis of the book? Concicsely state the thesis in one sentence.

**Core Mandate: Evidentialism**
- All claims you make MUST be backed by retrieved context or verified external sources.
- You MUST provide a citation for every piece of evidence. Example: [Source Name, Section/Page]
- Strictly forbidden: Do not invent, infer, or use metaphorical analysis. Your job is synthesis, not creation.

**Output Structure: Recursive Thematic Tree**
You MUST format your entire output according to the following structure:
- **Root Topic**: [The main subject of the analysis]
  - **Core Argument 1**: [A primary argument or theme]
    - **Evidence A**: [A direct quote or data point supporting Argument 1] [Citation A]
    - **Evidence B**: [Another direct quote or data point supporting Argument 1] [Citation B]
  - **Core Argument 2**: [A secondary argument or theme]
    - **Evidence C**: [A direct quote or data point supporting Argument 2] [Citation C]
"""
CORE_IDEAS_PROMPT = "Given the central thesis: '{thesis}', what are the 2-3 main supporting arguments or 'Core Ideas' presented in the text? List them clearly."
SUPPORTING_EVIDENCE_PROMPT = "Find specific examples, data, or anecdotes from the text that support the idea that: '{core_idea}'. Quote or paraphrase the evidence directly from the text."

CRITIC_PROMPT = """
You are a meticulous editor reviewing a podcast script. The script should follow a clear thematic tree structure: Central Thesis -> Core Ideas -> Supporting Evidence.
Ensure the following:
1.  **Structural Integrity**: Does the script contain a 'Central Thesis', at least one 'Core Idea', and 'Supporting Evidence' for each idea?
2.  **Clarity and Conciseness**: Is the thesis clear? Are the core ideas distinct? Is the evidence relevant?
3.  **Accuracy**: Does the evidence accurately reflect the provided text?

If the script is well-structured and accurate, respond with "LGTM". Otherwise, provide specific, actionable feedback for revision.
"""


# --- 4. 節點函數 ---

def router_node(state: AnalysisState):
    """
    Router Node: Classifies the book type (Instructional vs Narrative).
    This determines the strategy for the Analyst Agent.
    """
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
    """
    Draft Node: Generates the initial thematic tree analysis.
    """
    print("--- [Phase 1] Generating Thematic Tree Draft ---")
    original_text = state['original_text']
    
    # 1. Identify Thesis
    thesis_response = llm.invoke([
        SystemMessage(content=THESIS_PROMPT),
        HumanMessage(content=original_text)
    ])
    thesis = thesis_response.content.strip()
    
    # 2. Extract Core Ideas
    core_ideas_response = llm.invoke([
        SystemMessage(content=CORE_IDEAS_PROMPT.format(thesis=thesis)),
        HumanMessage(content=original_text)
    ])
    core_ideas_text = core_ideas_response.content.strip()
    # Simple parsing of core ideas. Assumes they are numbered or bulleted.
    core_ideas = [line.strip() for line in core_ideas_text.split('\n') if line.strip()]

    # 3. Gather Supporting Evidence for each Core Idea
    script_parts = [f"Central Thesis: {thesis}"]
    for i, idea in enumerate(core_ideas, 1):
        evidence_response = llm.invoke([
            SystemMessage(content=SUPPORTING_EVIDENCE_PROMPT.format(core_idea=idea)),
            HumanMessage(content=original_text)
        ])
        evidence = evidence_response.content.strip()
        script_parts.append(f"\nCore Idea {i}: {idea.lstrip('*- ')}")
        script_parts.append(f"Supporting Evidence: {evidence}")

    final_script = "\n".join(script_parts)

    return {"draft_analysis": final_script, "revision_count": 1}

def critique_node(state: AnalysisState):
    """
    Critique Node: Evaluates the draft against strict engineering standards.
    Acts as the 'Reflexion' step where the agent critiques its own work.
    """
    print(f"--- [Phase 2] 代碼審查 (Review Round {state.get('revision_count')}) ---")
    response = llm.invoke([
        SystemMessage(content=CRITIC_PROMPT),
        HumanMessage(content=f"待審查文檔：\n{state['draft_analysis']}")
    ])
    return {"critique_feedback": response.content}

def revise_node(state: AnalysisState):
    """
    Revise Node: Rewrites the analysis based on the critique feedback.
    """
    print("--- [Phase 3] Refactoring Based on Feedback ---")
    
    prompt = f"""
    The previous draft has been critiqued. Please revise it based on the following feedback.

    **Critique Feedback:**
    {state['critique_feedback']}

    **Original Draft:**
    {state['draft_analysis']}

    **Original Text:**
    {state['original_text']}

    Rewrite the script to address the feedback while maintaining the 'Thesis -> Core Idea -> Evidence' structure.
    """

    # The system message should guide the LLM to act as a scriptwriter/editor
    # For simplicity, we can reuse the core idea of being an analyst, but a more specific prompt could be used.
    # We will use a generic "you are a helpful assistant" here.

    response = llm.invoke([
        SystemMessage(content="You are an expert script editor. Revise the provided draft to address the user's critique."),
        HumanMessage(content=prompt)
    ])

    return {"draft_analysis": response.content, "revision_count": state.get("revision_count", 1) + 1}

# --- 5. 圖構建 ---

def should_continue(state: AnalysisState):
    """
    Decides whether to continue the loop (revise) or end.
    Conditions to End:
    1. Critique says "LGTM".
    2. Max retries reached.
    """
    feedback = state['critique_feedback']
    count = state['revision_count']
    
    if "LGTM" in feedback:
        print("--- Review 通過 (LGTM) ---")
        return END
    if count >= MAX_RETRIES:
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
