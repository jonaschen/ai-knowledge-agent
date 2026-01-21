import pytest
from unittest.mock import patch, MagicMock

# Mock the ChatVertexAI class before it's imported by the analyst_core module
with patch('langchain_google_vertexai.ChatVertexAI') as MockChatVertexAI:
    from src.analyst_core import app as analyst_app

@pytest.fixture
def mock_llm():
    """Fixture to provide a mock LLM instance."""
    mock_instance = MockChatVertexAI.return_value

    # Reset mocks for each test to ensure isolation
    mock_instance.invoke.reset_mock()

    # Default mock for the router to always return 'instructional'
    # The actual themed responses will be set within the test itself
    mock_instance.invoke.side_effect = [
        MagicMock(content="instructional"), # Router
        MagicMock(content="LGTM"), # Default Critic
    ]
    return mock_instance

def test_analyst_creates_thematic_tree_structure(mock_llm):
    """
    GIVEN a context_bundle with book text and author info
    WHEN the Analyst's analyze method is called
    THEN the resulting script should have a clear thematic tree structure
    """
    # 1. Arrange: Create a mock context_bundle and configure LLM responses
    mock_book_text = """
    The principle of 'Productive Laziness' is about maximizing output by minimizing wasted effort.
    The first pillar is 'Automate Everything'. For example, scripting daily reports saves hours.
    The second pillar is 'Decide Slowly'. For instance, rushing a tech stack choice leads to costly refactors.
    Ultimately, by being lazy about repetitive tasks and hasty decisions, one becomes more productive.
    """

    # Configure the mock LLM to return the thematic tree components in sequence
    # This simulates the multi-step prompting that will be implemented
    mock_llm.invoke.side_effect = [
        MagicMock(content="instructional"), # Router classifies the book type
        MagicMock(content="The core idea is to maximize productivity by strategically minimizing effort on low-impact tasks."), # Draft Node - Step 1 (Thesis)
        MagicMock(content="1. Automate Everything to reduce repetitive work.\n2. Decide Slowly to avoid costly mistakes."), # Draft Node - Step 2 (Core Ideas)
        MagicMock(content="Scripting daily reports is an example of automation."), # Draft Node - Step 3 (Evidence for Idea 1)
        MagicMock(content="Rushing a tech stack choice leads to refactors."), # Draft Node - Step 4 (Evidence for Idea 2)
        MagicMock(content="LGTM") # Critic approves the final script
    ]

    # We don't need verification_details for this test as the core logic is about the thematic tree
    mock_context_bundle = {"book_content": mock_book_text}

    # The input to the LangGraph app is a dictionary with the key 'original_text'
    app_input = {"original_text": mock_book_text}

    # 2. Act: Run the analysis by invoking the LangGraph app
    # The final state of the graph contains the 'draft_analysis'
    final_state = analyst_app.invoke(app_input)
    script = final_state.get("draft_analysis", "")

    # 3. Assert: Check for the thematic structure in the output
    assert "Central Thesis:" in script
    assert "Core Idea 1:" in script
    assert "Supporting Evidence:" in script
    assert "Core Idea 2:" in script
    # A more robust assertion would check for the second supporting evidence as well
    assert script.count("Supporting Evidence:") == 2, "Should have supporting evidence for each core idea"
