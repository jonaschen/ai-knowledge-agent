import pytest
from unittest.mock import patch, MagicMock, mock_open
from studio.review_agent import ReviewAgent, FailureAnalysis
import os
from dotenv import load_dotenv

# Ensure environment variables are loaded for the test context
load_dotenv()

@pytest.fixture
def review_agent():
    # Mock the GitHub and VertexAI clients to avoid real API calls
    with patch('studio.review_agent.Github') as MockGithub, \
         patch('studio.review_agent.ChatVertexAI') as MockChatVertexAI:
        # Create a mock github client and llm
        mock_github_client = MagicMock()
        mock_llm = MockChatVertexAI.return_value
        # Construct ReviewAgent with explicit repo_path and injected mocks
        agent = ReviewAgent(repo_path="/tmp/test_repo", github_client=mock_github_client, llm=mock_llm)
        return agent

def test_analyze_failure_with_ai(review_agent):
    """Test that analyze_failure correctly uses ChatVertexAI to process test output."""
    # Arrange: Mock the AI model and its response
    mock_llm = MagicMock()
    expected_analysis = FailureAnalysis(
        error_type="AssertionError",
        root_cause="The 'process' method in 'analyst_core.py' returned an empty list instead of a populated one, indicating a failure in the data transformation logic.",
        fix_suggestion="Verify the input data to 'process' and ensure the transformation logic correctly handles the provided fixture. Check for edge cases where the input might be valid but result in no output."
    )
    mock_llm.invoke.return_value = expected_analysis
    # Inject mock llm into the agent
    review_agent.llm = mock_llm

    failed_test_output = """
    =========================== FAILURES ===========================
    ____________________ test_analyst_process ____________________

        def test_analyst_process():
            analyst = AnalystCore()
            research_notes = [{"url": "http://example.com", "content": "Test content"}]
    >       assert analyst.process(research_notes) != []
    E       AssertionError: assert [] != []
    E        +  where [] = <bound method AnalystCore.process of <product.analyst_core.AnalystCore object at 0x10e8d6d10>>([{'url': 'http://example.com', 'content': 'Test content'}])
    E        +    where <bound method AnalystCore.process of <product.analyst_core.AnalystCore object at 0x10e8d6d10>> = <product.analyst_core.AnalystCore object at 0x10e8d6d10>.process

    product/tests/test_analyst.py:15: AssertionError
    """

    # Act
    analysis_result = review_agent.analyze_failure(failed_test_output)

    # Assert
    mock_llm.invoke.assert_called_once()
    assert analysis_result == expected_analysis

def test_write_history(review_agent):
    """Test that write_history appends to the history file in the correct format."""
    pr_number = 101
    analysis = FailureAnalysis(
        error_type="PydanticValidationError",
        root_cause="Mock object was passed to a Pydantic model which expects concrete values.",
        fix_suggestion="When testing Pydantic models, use dictionaries or string literals instead of MagicMock objects for input data."
    )

    m_open = mock_open()
    with patch('builtins.open', m_open):
        review_agent.write_history(pr_number, analysis)
        m_open.assert_called_once_with('studio/review_history.md', 'a', encoding='utf-8')
        handle = m_open()
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)

        assert f"## [PR #{pr_number}] ReviewAgent Failure" in written_content
        assert "- **Error Type**: PydanticValidationError" in written_content
        assert "- **Root Cause**: Mock object was passed to a Pydantic model which expects concrete values." in written_content
        assert "- **Fix Suggestion**: When testing Pydantic models, use dictionaries or string literals instead of MagicMock objects for input data." in written_content
