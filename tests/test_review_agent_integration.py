import subprocess
import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock

from studio.review_agent import ReviewAgent

def run_git_command(command, cwd):
    """Helper to run git commands in a specific directory."""
    subprocess.run(command, check=True, cwd=cwd, shell=True, capture_output=True)

@pytest.fixture
def git_repo(tmp_path):
    """Creates a temporary git repo simulating our project environment."""
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    # 1. Init repo and configure user
    run_git_command("git init -b main", repo_path)
    run_git_command('git config user.email "test@example.com"', repo_path)
    run_git_command('git config user.name "Test User"', repo_path)

    # 2. Create a file and a passing test on main
    (repo_path / "app.py").write_text("def get_status():\\n    return 'ok'")
    (repo_path / "tests").mkdir()
    (repo_path / "tests/test_app.py").write_text(
        "from app import get_status\\n\\ndef test_status():\\n    assert get_status() == 'ok'"
    )
    (repo_path / "pytest.ini").write_text("[pytest]\\ntestpaths = tests")
    run_git_command("git add .", repo_path)
    run_git_command("git commit -m 'Initial commit with passing test'", repo_path)

    # 3. Create a new branch with a breaking change
    run_git_command("git checkout -b feature/breaking-change", repo_path)
    (repo_path / "app.py").write_text("def get_status():\\n    return 'broken'") # This will fail the test
    run_git_command("git commit -am 'Introduce breaking change'", repo_path)

    # 4. Return to main to simulate the agent's starting state
    run_git_command("git checkout main", repo_path)

    return repo_path

def test_process_prs_rejects_pr_with_failing_tests(git_repo):
    """
    This test will FAIL before the fix and PASS after the fix.
    It proves the bug: the agent currently merges a PR with failing tests.
    """
    # Arrange: Mock a PR object and the agent
    mock_pr = MagicMock()
    mock_pr.number = 1
    mock_pr.head.ref = "feature/breaking-change"
    # The fetch refspec for PRs
    mock_pr.fetch_ref = f"pull/{mock_pr.number}/head:pr-{mock_pr.number}"

    def fake_merge():
        run_git_command(f"git merge --no-ff -m 'Merge PR #{mock_pr.number}' {mock_pr.head.ref}", git_repo)
    mock_pr.merge = fake_merge
    mock_pr.create_issue_comment.return_value = True

    agent = ReviewAgent(repo_path=str(git_repo), github_client=MagicMock())

    original_cwd = os.getcwd()
    os.chdir(git_repo)
    try:
        run_git_command(f"git remote add origin .", git_repo)
        run_git_command(f"git update-ref refs/pull/{mock_pr.number}/head refs/heads/{mock_pr.head.ref}", git_repo)

        agent.process_open_prs([mock_pr])
    finally:
        os.chdir(original_cwd)

    main_branch_content = (git_repo / "app.py").read_text()
    assert "broken" not in main_branch_content, "BUG: The breaking change was merged into main!"