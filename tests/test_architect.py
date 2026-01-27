import pytest
from unittest.mock import patch, MagicMock
import os
from langchain_core.messages import AIMessage

from studio.architect import Architect

@patch('studio.architect.ChatVertexAI')
@patch('studio.architect.Github')
def test_architect_injects_knowledge_base_into_prompt(mock_github, mock_chat_vertex_ai, tmp_path):
    """
    Verify the Architect loads knowledge files and injects them into the LLM prompt.
    """
    # Configure the mock to return an AIMessage object when called
    mock_llm_instance = mock_chat_vertex_ai.return_value
    mock_llm_instance.return_value = AIMessage(content="Mocked LLM Response")

    # 1. Setup: Create mock knowledge base files
    studio_dir = tmp_path / "studio"
    studio_dir.mkdir()
    rules_md = studio_dir / "rules.md"
    rules_md.write_text("### 1.1 Pydantic Model Mocking\n* **Problem:** Passing `MagicMock` causes `ValidationError`.\n* **Solution:** Always use **concrete types (literals)**.")

    history_md = studio_dir / "review_history.md"
    history_md.write_text("## [PR #123] Some Failure\n- **Root Cause**: Used MagicMock with Pydantic.")

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("This is the constitution.")

    # 2. The user makes a request that violates a known rule
    user_request = "Please fix the failing test by using MagicMock for the Pydantic model."

    # 3. Instantiate the Architect with paths to our mock files, mocking the environment variable
    with patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"}):
        architect = Architect(
            repo_name="test/repo",
            rules_path=str(rules_md),
            history_path=str(history_md),
            agents_md_path=str(agents_md)
        )

    # 4. Run the method being tested
    architect.plan_feature(user_request)

    # 5. Assert: Check that the prompt sent to the LLM contains the required elements
    mock_llm_instance.assert_called_once()
    prompt_sent_to_llm = mock_llm_instance.call_args[0][0].to_string()

    # A. Check for the Knowledge Base section
    assert "=== KNOWLEDGE BASE ===" in prompt_sent_to_llm

    # B. Check for content from rules.md
    assert "Pydantic Model Mocking" in prompt_sent_to_llm
    assert "Always use **concrete types (literals)**" in prompt_sent_to_llm

    # C. Check for content from review_history.md
    assert "Used MagicMock with Pydantic" in prompt_sent_to_llm

    # D. Check for the new instruction
    assert "cross-reference the User Request with the Knowledge Base" in prompt_sent_to_llm
    assert "explicitly add a constraint in the Issue Body" in prompt_sent_to_llm
