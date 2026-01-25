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
    
    def __init__(self, repo_name: Optional[str] = None, root_path: str = "."):
        self.root_path = root_path
        if repo_name:
            token = os.getenv("GITHUB_TOKEN")
            if not token:
                raise ValueError("❌ CRITICAL: GITHUB_TOKEN not found in .env file. Architect cannot work without it.")

            self.github = Github(os.getenv("GITHUB_TOKEN"))
            self.repo = self.github.get_repo(repo_name)
        else:
            self.github = None
            self.repo = None
        
        # 使用 Gemini 2.5 Pro 作為大腦，Temperature 稍高以利於規劃
        self.llm = ChatVertexAI(
            model_name="gemini-2.5-pro",
            temperature=0.2, 
            max_output_tokens=8192
        )
        
        # Load constitution from the specified root path
        try:
            agents_path = os.path.join(self.root_path, "AGENTS.md")
            with open(agents_path, "r") as f:
                self.constitution = f.read()
        except FileNotFoundError:
            print("⚠️ Warning: AGENTS.md not found. Architect is operating without a constitution.")
            self.constitution = "Focus on reliability and modularity."

        # Load rules.md (long-term memory)
        try:
            rules_path = os.path.join(self.root_path, "studio", "rules.md")
            with open(rules_path, 'r') as f:
                self.rules = f.read()
        except FileNotFoundError:
            self.rules = "# No rules defined yet."

        # Load review_history.md (short-term memory)
        try:
            history_path = os.path.join(self.root_path, "studio", "review_history.md")
            with open(history_path, 'r') as f:
                self.history = f.read()
        except FileNotFoundError:
            self.history = "# No recent failures recorded."

    def plan_feature(self, user_request: str) -> str:
        """
        核心邏輯：將需求轉化為 Issue
        """
        print(f"🏗️ Architect is analyzing request: '{user_request}'...")
        
        prompt = f"""
You are the Chief Software Architect for the 'Deep Context Reader' project.
Your goal is to translate a user request into a GitHub Issue for the developer, Jules.
You MUST follow the principles and structure defined in the constitution.

=== YOUR CONSTITUTION (AGENTS.md) ===
{self.constitution}

=== DESIGN PATTERNS (MUST FOLLOW) ===
{self.rules}

=== RECENT FAILURES (AVOID THESE) ===
{self.history}

=== USER REQUEST ===
{user_request}

=== YOUR TASK ===
Draft a GitHub Issue with a title and body.
The issue must follow our strict TDD mandate:
1.  **Step 1: The Test:** Define a new Python test case in the `tests/` directory that will fail until the feature is implemented.
2.  **Step 2: The Implementation:** Provide clear, file-specific instructions for the developer to make the test pass.
3.  **Acceptance Criteria:** List 2-3 bullet points Erfolgskriterien.

Output ONLY the GitHub Issue in the specified format. Do not add any other commentary.
"""
        return prompt

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
    
    architect = Architect(repo_name=REPO_NAME)
    plan = architect.plan_feature(user_request)
    architect.publish_issue(plan)
