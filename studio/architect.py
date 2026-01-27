import os
import sys
from typing import Optional
from dotenv import load_dotenv
from github import Github
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 確保能讀取到環境變數
load_dotenv()

class Architect:
    """
    The Architect is the bridge between Human Strategy and AI Execution.
    It translates high-level goals into precise, TDD-compliant GitHub Issues.
    """
    
    def __init__(self, repo_name: str, rules_path: str = "studio/rules.md", history_path: str = "studio/review_history.md"):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("❌ CRITICAL: GITHUB_TOKEN not found in .env file. Architect cannot work without it.")

        self.github = Github(os.getenv("GITHUB_TOKEN"))

        self.repo = self.github.get_repo(repo_name)
        
        # 使用 Gemini 2.5 Pro 作為大腦，Temperature 稍高以利於規劃
        self.llm = ChatVertexAI(
            model_name="gemini-2.5-pro",
            temperature=0.2, 
            max_output_tokens=8192
        )
        
        # 載入憲法 (Constitution)
        # 注意：搬家後 AGENTS.md 應該還是在根目錄，所以路徑可能需要調整
        try:
            with open("AGENTS.md", "r") as f:
                self.constitution = f.read()
        except FileNotFoundError:
            print("⚠️ Warning: AGENTS.md not found. Architect is operating without a constitution.")
            self.constitution = "Focus on reliability and modularity."

        # Load Long-term Memory (Rules)
        try:
            with open(rules_path, "r") as f:
                self.rules = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ CRITICAL: Rules file not found at {rules_path}")

        # Load Active Memory (Review History)
        try:
            with open(history_path, "r") as f:
                self.review_history = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ CRITICAL: Review history file not found at {history_path}")

    def plan_feature(self, user_request: str) -> str:
        """
        核心邏輯：將需求轉化為 Issue
        """
        print(f"🏗️ Architect is analyzing request: '{user_request}'...")
        
        system_prompt = """
        You are the Chief Software Architect for an AI Software Studio.
        Your goal is to manage the development of the 'Deep Context Reader' project.
        
        === YOUR CONSTITUTION (AGENTS.md) ===
        {constitution}
        =====================================

        === KNOWLEDGE BASE ===
        RULES (rules.md):
        {rules}

        RECENT FAILURES (review_history.md):
        {review_history}
        =======================================

        === TEAM STRUCTURE ===
        1. Studio Team (Internal Tools): Responsible for the management layer (studio/).
           - Components: Architect, ReviewAgent, ProductManager, Rules, History.
           - Goal: Build tools that build the product.

        2. Product Team (The Application): Responsible for the core content generation system (product/).
           - Components: Curator, Researcher, Analyst, Broadcaster.
           - Goal: The "Deep Context Reader" system.

        === TDD MANDATE ===
        We follow strict Test-Driven Development (TDD).
        For every bug fix or feature request, you MUST instruct the developer (Jules) to:
        1. Create a Reproduction Script or Unit Test FIRST.
        2. Ensure the test fails (Red).
        3. Write code to pass the test (Green).
        
        === USER REQUEST ===
        {request}
        
        === INSTRUCTIONS ===
        Analyze the request to determine which team is responsible (Studio Team or Product Team).
        Before generating the Issue, cross-reference the User Request with the Knowledge Base. If a known anti-pattern is detected (e.g., Pydantic Mocking), explicitly add a constraint in the Issue Body.
        Draft a GitHub Issue in the following format. 
        Be extremely specific about file paths (e.g., product/curator.py, tests/test_curator.py).
        
        Format:
        Title: [Team Name] [Tag] <Concise Title>
        Body:
        @jules
        <Context & Objective>
        
        ### Step 1: The Test (The Spec)
        <Provide a specific test case or script>
        
        ### Step 2: The Implementation
        <Provide technical guidance on what to change>
        
        ### Acceptance Criteria
        <Bullet points>
        """
        
        prompt = ChatPromptTemplate.from_template(system_prompt)
        chain = prompt | self.llm | StrOutputParser()
        
        return chain.invoke({
            "constitution": self.constitution,
            "rules": self.rules,
            "review_history": self.review_history,
            "request": user_request
        })

    def publish_issue(self, issue_content: str):
        """
        發布 Issue 到 GitHub
        """
        # 簡單的解析器 (假設 LLM 輸出格式正確)
        lines = issue_content.strip().split("\n")
        title = lines[0].replace("Title:", "").strip()
        
        # 尋找 Body 的開始
        body_start = 0
        for i, line in enumerate(lines):
            if "Body:" in line:
                body_start = i + 1
                break
        
        body = "\n".join(lines[body_start:]).strip()
        
        print("\n" + "="*50)
        print(f"Proposed Issue: {title}")
        print("-" * 50)
        print(body[:500] + "...\n(content truncated for preview)")
        print("="*50)
        
        confirm = input(">> Approve and Publish to Jules? (y/n): ")
        if confirm.lower() == 'y':
            issue = self.repo.create_issue(
                title=title,
                body=body,
                labels=["jules", "architect-approved"]
            )
            print(f"🚀 Published Issue #{issue.number}. Jules is on it.")
        else:
            print("❌ Cancelled.")

# --- CLI Entry Point ---
if __name__ == "__main__":
    # 讀取 Repo 名稱 (建議從 .env 讀取或直接寫死)
    REPO_NAME = os.getenv("GITHUB_REPO_NAME", "jonaschen/ai-knowledge-agent")
    
    if len(sys.argv) < 2:
        print("Usage: python -m studio.architect 'Your feature request here'")
        sys.exit(1)
        
    user_request = sys.argv[1]
    
    architect = Architect(REPO_NAME)
    plan = architect.plan_feature(user_request)
    architect.publish_issue(plan)
