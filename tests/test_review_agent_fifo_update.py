import subprocess
import pytest
import os
import sys
from unittest.mock import MagicMock, patch

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

    # Allow pushing to current branch (for test simulation)
    run_git_command("git config receive.denyCurrentBranch ignore", repo_path)

    # 2. Create basic structure
    (repo_path / "studio").mkdir()
    (repo_path / "studio/review_agent.py").write_text("# Mock agent file")

    (repo_path / "tests").mkdir()
    (repo_path / "tests/test_dummy.py").write_text("def test_pass(): assert True")

    # Create pytest.ini
    (repo_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests")

    run_git_command("git add .", repo_path)
    run_git_command("git commit -m 'Initial commit'", repo_path)

    return repo_path

def test_process_open_prs_updates_history_on_failure(git_repo):
    """
    Verifies that when a PR fails tests:
    1. review_history.md is updated in the PR branch.
    2. The update is committed and pushed to the PR branch.
    """
    # Arrange: Create a failing feature branch
    run_git_command("git checkout -b feature/fail", git_repo)
    (git_repo / "tests/test_fail.py").write_text("def test_fail(): assert False")
    run_git_command("git add .", git_repo)
    run_git_command("git commit -m 'Add failing test'", git_repo)

    # Switch back to main to simulate agent starting state
    run_git_command("git checkout main", git_repo)

    # Mock PR object
    mock_pr = MagicMock()
    mock_pr.number = 123
    mock_pr.head.ref = "feature/fail"
    # We set origin to be the repo itself for this test
    mock_pr.fetch_ref = f"pull/{mock_pr.number}/head:pr-{mock_pr.number}"

    # Mock Github client
    mock_gh = MagicMock()

    # Initialize Agent
    agent = ReviewAgent(repo_path=str(git_repo), github_client=mock_gh)

    # Setup refs for fetch to work (simulating the PR ref existence)
    # Origin is the repo itself
    run_git_command(f"git remote add origin .", git_repo)
    run_git_command(f"git update-ref refs/pull/{mock_pr.number}/head refs/heads/{mock_pr.head.ref}", git_repo)

    # Run the process
    # We mock write_history to use repo_path (if we haven't patched the code yet, this test might fail/behave weirdly unless we fix the code first)
    # But wait, we are modifying the code to use repo_path.
    # For this test to pass, the code MUST be modified to use repo_path for writing history.

    with patch.dict(os.environ, {"UPDATE_REVIEW_HISTORY": "true"}):
        agent.process_open_prs([mock_pr])

    # Assertions

    # 1. Check if we are back on main (cleanup)
    result = subprocess.run(['git', 'branch', '--show-current'], cwd=git_repo, capture_output=True, text=True)
    assert result.stdout.strip() == "main"

    # 2. Check feature/fail branch for the commit
    # We fetch the feature branch to check its content (it was pushed to 'origin' which is local repo)
    # Since origin is ., the push updated refs/heads/feature/fail directly?
    # Wait, pushing to non-bare repo's checked out branch (if it was checked out) is tricky.
    # But we checked out 'pr-123' then 'main'. 'feature/fail' is not checked out. So push should succeed.

    run_git_command("git checkout feature/fail", git_repo)

    history_file = git_repo / "studio/review_history.md"
    assert history_file.exists(), "review_history.md was not created in the feature branch"

    content = history_file.read_text()
    assert "FAILED" in content
    assert "test_fail.py" in content # Component detection might be tricky if not standardized, but let's see.

    # Verify commit message
    log = subprocess.run(['git', 'log', '-1', '--pretty=%s'], cwd=git_repo, capture_output=True, text=True).stdout.strip()
    assert log == f"docs: Update review history for pr-{mock_pr.number}"
