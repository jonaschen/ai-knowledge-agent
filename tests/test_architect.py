import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from studio.architect import Architect, ContextLoader, IssueFormatter

# --- Test The Components ---

@patch('studio.architect.Path')
def test_context_loader_reads_files(MockPath):
    """
    Tests that the ContextLoader correctly reads and returns content from key files.
    """
    mock_files = {
        "AGENTS.md": "Constitution Content",
        "studio/rules.md": "Rules Content",
        "studio/review_history.md": "History Content"
    }

    def configure_mock_path(path_str):
        # This function will be the side_effect for the Path constructor.
        # It creates a mock instance for each path string.
        mock_instance = MagicMock(spec=Path)
        # Configure the read_text method on this specific instance
        mock_instance.read_text.return_value = mock_files[path_str]
        # Set the name for better debuggability (optional)
        mock_instance.name = path_str
        return mock_instance

    # When Path() is called in the code under test, it will trigger this side_effect.
    MockPath.side_effect = configure_mock_path

    # Act
    loader = ContextLoader()
    context = loader.load_context()

    # Assert
    assert context["constitution"] == "Constitution Content"
    assert context["rules"] == "Rules Content"
    assert context["history"] == "History Content"

    # Verify that Path() was called with the correct arguments
    assert MockPath.call_count == 3
    MockPath.assert_any_call("AGENTS.md")
    MockPath.assert_any_call("studio/rules.md")
    MockPath.assert_any_call("studio/review_history.md")

def test_issue_formatter_creates_markdown():
    """
    Tests that the IssueFormatter correctly formats a GitHub issue.
    """
    formatter = IssueFormatter()
    context = {
        "constitution": "Test Constitution",
        "rules": "Test Rules",
        "history": "Test History"
    }
    user_request = "Create a new feature."

    issue_content = formatter.format(user_request, context)

    assert "Title: [Feature] Create a new feature." in issue_content
    assert "@jules" in issue_content
    assert "### Step 1: The Test (The Spec)" in issue_content
    assert "### Step 2: The Implementation" in issue_content

# --- Test The Orchestrator (Architect) ---

def test_architect_uses_dependency_injection():
    """
    Tests that the main Architect class orchestrates its dependencies correctly.
    """
    # Arrange
    mock_loader = MagicMock(spec=ContextLoader)
    mock_formatter = MagicMock(spec=IssueFormatter)

    mock_context = {"data": "mock_context"}
    mock_loader.load_context.return_value = mock_context
    mock_formatter.format.return_value = "Formatted GitHub Issue"

    user_request = "Refactor the curator."

    # Act
    architect = Architect(loader=mock_loader, formatter=mock_formatter)
    issue = architect.draft_issue(user_request)

    # Assert
    mock_loader.load_context.assert_called_once()
    mock_formatter.format.assert_called_once_with(user_request, mock_context)
    assert issue == "Formatted GitHub Issue"
