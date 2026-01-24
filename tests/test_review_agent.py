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
    with patch('studio.review_agent.Github'), \
         patch('studio.review_agent.ChatVertexAI'):
        # Ensure GITHUB_TOKEN is set for the constructor
        assert os.getenv("GITHUB_TOKEN"), "GITHUB_TOKEN not found in .env"
        agent = ReviewAgent(repo_name="test/repo")
        return agent

def test_analyze_failure_with_ai(review_agent):
    """
    Test that analyze_failure correctly uses ChatVertexAI to process test output.
    """
    # 1. Arrange: Mock the AI model and its response
    mock_llm = MagicMock()
    # This is the structured data we expect the AI to return
    expected_analysis = FailureAnalysis(
        error_type="AssertionError",
        root_cause="The 'process' method in 'analyst_core.py' returned an empty list instead of a populated one, indicating a failure in the data transformation logic.",
        fix_suggestion="Verify the input data to 'process' and ensure the transformation logic correctly handles the provided fixture. Check for edge cases where the input might be valid but result in no output."
    )
    mock_llm.invoke.return_value = expected_analysis
    review_agent.llm = mock_llm

    # A sample of realistic pytest failure output
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

    # 2. Act: Call the method to be tested
    analysis_result = review_agent.analyze_failure(failed_test_output)

    # 3. Assert: Verify the results
    mock_llm.invoke.assert_called_once()
    assert analysis_result == expected_analysis

def test_write_history(review_agent):
    """
    Test that write_history appends to the history file in the correct format.
    """
    # 1. Arrange
    pr_number = 101
    analysis = FailureAnalysis(
        error_type="PydanticValidationError",
        root_cause="Mock object was passed to a Pydantic model which expects concrete values.",
        fix_suggestion="When testing Pydantic models, use dictionaries or string literals instead of MagicMock objects for input data."
    )

    # Mock open() to capture what's being written to the file
    m_open = mock_open()
    with patch('builtins.open', m_open):
        # 2. Act
        review_agent.write_history(pr_number, analysis)

        # 3. Assert
        m_open.assert_called_once_with('studio/review_history.md', 'a', encoding='utf-8')
        handle = m_open()
        
        # Grab all calls to write() and join them
        written_content = "".join(call.args[0] for call in handle.write.call_args_list)

        assert f"## [PR #{pr_number}] ReviewAgent Failure" in written_content
        assert "- **Error Type**: PydanticValidationError" in written_content
        assert "- **Root Cause**: Mock object was passed to a Pydantic model which expects concrete values." in written_content
        assert "- **Fix Suggestion**: When testing Pydantic models, use dictionaries or string literals instead of MagicMock objects for input data." in written_content