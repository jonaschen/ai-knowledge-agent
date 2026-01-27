import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from github import Github
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# Ensure environment variables are loaded
load_dotenv()

class Architect:
    """
    The Architect is the bridge between Human Strategy and AI Execution.
    It translates high-level goals into precise, TDD-compliant GitHub Issues.
    """
    
    def __init__(self, repo_name: str, agents_md_path: str = "AGENTS.md", rules_path: str = "studio/rules.md", history_path: str = "studio/review_history.md"):
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("❌ CRITICAL: GITHUB_TOKEN not found in .env file. Architect cannot work without it.")

        self.github = Github(os.getenv("GITHUB_TOKEN"))
        self.repo = self.github.get_repo(repo_name)
        
        # Use Gemini 2.5 Pro as the brain, with a slightly higher temperature for planning.
        self.llm = ChatVertexAI(
            model_name="gemini-2.5-pro",
            temperature=0.2, 
            max_output_tokens=8192
        )
        
        # Load constitution, rules, and history. Paths can be overridden for testing.
        self.agents_md_path = Path(agents_md_path)
        self.rules_path = Path(rules_path)
        self.history_path = Path(history_path)

        if not self.agents_md_path.is_file():
            raise FileNotFoundError(f"Constitution not found at {self.agents_md_path}")
        if not self.rules_path.is_file():
            raise FileNotFoundError(f"Long-term memory not found at {self.rules_path}")
        if not self.history_path.is_file():
            raise FileNotFoundError(f"Active memory not found at {self.history_path}")

        self.constitution = self.agents_md_path.read_text()
        self.rules = self.rules_path.read_text()
        self.review_history = self.history_path.read_text()

    def plan_feature(self, user_request: str) -> str:
        """
        核心邏輯：將需求轉化為 Issue
        """
        print(f"🏗️ Architect is analyzing request: '{user_request}'...")
        
        system_prompt = f"""
You are the Chief Software Architect for an AI Software Studio.
Your goal is to translate user requests into TDD-based GitHub Issues for the developer, Jules.

=== YOUR CONSTITUTION (AGENTS.md) ===
{self.constitution}

=== KNOWLEDGE BASE ===
This section contains long-term rules and recent failures. Use it to guide your plan and prevent repeating mistakes.

--- LONG-TERM MEMORY (studio/rules.md) ---
{self.rules}

--- ACTIVE MEMORY (studio/review_history.md) ---
{self.review_history}
---

=== INSTRUCTIONS ===
You will now receive a user request. Your task is to generate a GitHub issue.

**CRITICAL GUIDANCE**: Before generating the Issue, cross-reference the User Request with the Knowledge Base. If a known anti-pattern is detected (e.g., Pydantic Mocking from rules.md), you MUST explicitly add a "Constraint" section in the Issue Body to warn the developer. explicitly add a constraint in the Issue Body

Follow the TDD mandate: Define the test first, then the implementation.
Be extremely specific about file paths.

User Request: "{user_request}"

Generate the GitHub Issue now.
"""
        
        prompt = ChatPromptTemplate.from_template("{prompt}")
        chain = prompt | self.llm | StrOutputParser()
        
        return chain.invoke({"prompt": system_prompt})

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
