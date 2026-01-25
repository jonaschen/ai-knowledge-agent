
import pytest
from unittest.mock import patch
from studio.architect import Architect
import os

@patch('studio.architect.ChatVertexAI')
def test_architect_loads_and_uses_memory_files(mock_chat_vertex_ai, tmp_path):
    """
    Ensures the Architect loads and includes rules.md and review_history.md in its prompt.
    """
    # Configure the mock to return a string
    mock_llm = mock_chat_vertex_ai.return_value
    mock_llm.invoke.return_value = ""

    # 1. Setup: Create mock memory files in a temporary directory
    studio_dir = tmp_path / "studio"
    studio_dir.mkdir()

    rules_content = "RULE_MARKER: Always use context managers for files."
    (studio_dir / "rules.md").write_text(rules_content)

    history_content = "HISTORY_MARKER: PR #123 failed due to API timeout."
    (studio_dir / "review_history.md").write_text(history_content)

    # Create a dummy AGENTS.md as it's a required file
    agents_content = "CONSTITUTION_MARKER"
    (tmp_path / "AGENTS.md").write_text(agents_content)

    # 2. Action: Instantiate the Architect, pointing to our temp directory
    # We pass the root path to the constructor for testability.
    architect = Architect(root_path=str(tmp_path))

    # Generate a plan
    user_request = "Add a new feature."

    # In the refactored Architect, the prompt is constructed but not sent to the LLM.
    # We can directly inspect the prompt string.
    generated_prompt = architect.plan_feature(user_request)


    # 3. Assert: Check if the memory content is present in the generated prompt
    assert "=== DESIGN PATTERNS (MUST FOLLOW) ===" in generated_prompt
    assert rules_content in generated_prompt

    assert "=== RECENT FAILURES (AVOID THESE) ===" in generated_prompt
    assert history_content in generated_prompt

    # Also ensure the constitution is still being loaded
    assert agents_content in generated_prompt
