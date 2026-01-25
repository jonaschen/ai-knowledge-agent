import unittest
from unittest.mock import patch, MagicMock
import subprocess

# We will create the ReviewAgent class that makes this test pass
from studio.review_agent import ReviewAgent

class TestReviewAgent(unittest.TestCase):

    @patch('subprocess.run')
    @patch('studio.review_agent.git.Repo')
    def test_process_pr_success_and_merge(self, mock_repo, mock_subprocess_run):
        """
        GIVEN a pull request is ready for review
        WHEN the tests pass
        THEN the agent should merge the branch.
        """
        # Arrange: Mock a successful pytest run
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="Success", stderr="")

        # Arrange: Mock the Git repository
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.merge_base.return_value = ['some_commit_hash']

        # Act
        agent = ReviewAgent(repo_path='.')
        result = agent.process_pr(branch_name='feature/new-thing')

        # Assert
        mock_subprocess_run.assert_called_once_with(['pytest'], capture_output=True, text=True, check=False)
        mock_repo_instance.git.merge.assert_called_once_with('feature/new-thing')
        self.assertTrue(result, "Process should return True on success")
        print("\n✅ test_process_pr_success_and_merge: PASSED")


    @patch('subprocess.run')
    @patch('studio.review_agent.git.Repo')
    def test_process_pr_failure_no_merge(self, mock_repo, mock_subprocess_run):
        """
        GIVEN a pull request is ready for review
        WHEN the tests fail
        THEN the agent should NOT merge the branch.
        """
        # Arrange: Mock a failed pytest run
        mock_subprocess_run.return_value = MagicMock(returncode=1, stdout="Failure", stderr="Test failed")

        # Arrange: Mock the Git repository
        mock_repo_instance = mock_repo.return_value

        # Act
        agent = ReviewAgent(repo_path='.')
        result = agent.process_pr(branch_name='feature/broken-thing')

        # Assert
        mock_subprocess_run.assert_called_once_with(['pytest'], capture_output=True, text=True, check=False)
        mock_repo_instance.git.merge.assert_not_called()
        self.assertFalse(result, "Process should return False on failure")
        print("\n✅ test_process_pr_failure_no_merge: PASSED")

if __name__ == '__main__':
    unittest.main()