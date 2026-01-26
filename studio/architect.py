# studio/architect.py
from pathlib import Path

class ContextLoader:
    """
    Responsible for loading all necessary context from the file system.
    SRP: Its only job is to read files.
    """
    def load_context(self) -> dict[str, str]:
        """Loads constitution, rules, and history into a dictionary."""
        # Note: Use absolute paths or relative paths from a known root
        # to ensure this works regardless of where it's called from.
        # For now, we assume execution from the root directory.
        return {
            "constitution": Path("AGENTS.md").read_text(),
            "rules": Path("studio/rules.md").read_text(),
            "history": Path("studio/review_history.md").read_text(),
        }

class IssueFormatter:
    """
    Responsible for formatting the loaded context into a GitHub issue.
    SRP: Its only job is to format strings.
    """
    def format(self, user_request: str, context: dict[str, str]) -> str:
        """Generates a GitHub issue markdown string from a user request and context."""
        # This is a simplified example. You will port the existing
        # issue generation logic here.
        # A simple heuristic for the title tag:
        tag = "Feature"
        if "refactor" in user_request.lower():
            tag = "Refactor"
        elif "fix" in user_request.lower() or "bug" in user_request.lower():
            tag = "Bugfix"

        title = f"[{tag}] {user_request}"

        # The body will be a complex template using the context.
        # For this task, a placeholder is sufficient.
        body = f"""
@jules

This is an auto-generated issue based on your request: "{user_request}"

### Step 1: The Test (The Spec)
<Provide a specific test case or script>

### Step 2: The Implementation
<Provide technical guidance on what to change>

### Acceptance Criteria
<Bullet points>
"""
        return f"Title: {title}\nBody:\n{body}"


class Architect:
    """
    Orchestrates the process of drafting a TDD issue.
    DIP: Depends on abstractions (via constructor injection) not concrete implementations.
    """
    def __init__(self, loader: ContextLoader, formatter: IssueFormatter):
        self.loader = loader
        self.formatter = formatter

    def draft_issue(self, user_request: str) -> str:
        """
        Drafts a complete GitHub issue.
        1. Loads context.
        2. Formats the issue.
        """
        print("Architect: Loading context...")
        context = self.loader.load_context()
        print("Architect: Formatting issue...")
        issue = self.formatter.format(user_request, context)
        print("Architect: Issue drafted.")
        return issue

# Optional: Add a main block to allow standalone execution for testing
if __name__ == '__main__':
    # This demonstrates how the components are wired together in production.
    # Our tests will inject mocks instead.
    default_loader = ContextLoader()
    default_formatter = IssueFormatter()
    architect_agent = Architect(loader=default_loader, formatter=default_formatter)
    
    request = "Refactor studio/architect.py to follow SOLID principles."
    generated_issue = architect_agent.draft_issue(request)
    print("\\n--- GENERATED ISSUE ---")
    print(generated_issue)
