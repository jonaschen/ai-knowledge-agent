import unittest
from unittest.mock import patch, MagicMock, call
import datetime

# Import the class to be tested
from studio.review_agent import ReviewAgent

# Mock PR data structure that matches the `gh` CLI JSON output
def create_mock_pr(number, branch_name, created_at):
    iso_time = created_at.isoformat() + "Z"
    return {
        "number": number,
        "headRefName": branch_name,
        "createdAt": iso_time
    }

class TestReviewAgentWorkflow(unittest.TestCase):

    @patch('studio.review_agent.get_open_prs')
    @patch('studio.review_agent.run_command')
    def test_processes_prs_in_fifo_order(self, mock_run_command, mock_get_open_prs):
        """
        Ensures the agent fetches PRs and processes the oldest one first.
        """
        # Arrange
        # The agent should sort these to process #1 (older) first
        mock_get_open_prs.return_value = [
            create_mock_pr(2, 'feature-new', datetime.datetime(2023, 10, 27)),
            create_mock_pr(1, 'feature-old', datetime.datetime(2023, 10, 26)),
        ]
        mock_run_command.return_value = (0, "Success", "")
        agent = ReviewAgent()

        # Act
        agent.run()

        # Assert
        git_checkout_calls = [
            c for c in mock_run_command.call_args_list if len(c.args[0]) > 1 and c.args[0][:2] == ['git', 'checkout']
        ]
        self.assertTrue(len(git_checkout_calls) >= 2, "Expected at least two checkout calls for PR branches")
        # Verify the first branch checked out is the oldest PR
        self.assertEqual(git_checkout_calls[0].args[0][2], 'feature-old')
        # Verify the second branch checked out is the newer PR (after the first is processed)
        self.assertEqual(git_checkout_calls[2].args[0][2], 'feature-new')


    @patch('studio.review_agent.get_open_prs')
    @patch('studio.review_agent.run_command')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handles_test_failure_correctly(self, mock_open, mock_run_command, mock_get_open_prs):
        """
        Ensures that on test failure, it updates review_history.md and pushes to the PR branch.
        """
        # Arrange
        mock_get_open_prs.return_value = [create_mock_pr(101, 'bugfix-branch', datetime.datetime.now())]

        # Simulate a pytest command failure
        def command_side_effect(command):
            if command == ['pytest']:
                return (1, "== FAILURES ==", "E       assert 1 == 2")
            return (0, "Success", "")
        mock_run_command.side_effect = command_side_effect
        agent = ReviewAgent()

        # Act
        agent.run()

        # Assert
        # 1. Verify that the history file was opened in append mode
        mock_open.assert_called_with('studio/review_history.md', 'a')
        handle = mock_open()

        # 2. Verify that a log entry was written
        handle.write.assert_called_once()
        written_text = handle.write.call_args[0][0]
        self.assertIn("[PR #101]", written_text)
        self.assertIn("Root Cause: assert 1 == 2", written_text)

        # 3. Verify the correct sequence of git commands was executed
        expected_calls = [
            call(['git', 'checkout', 'bugfix-branch']),
            call(['pytest']),
            call(['git', 'add', 'studio/review_history.md']),
            call(['git', 'commit', '-m', 'docs: Log test failure for PR #101']),
            call(['git', 'push', 'origin', 'bugfix-branch']),
        ]
        mock_run_command.assert_has_calls(expected_calls, any_order=False)

        # 4. Verify that a merge was NOT attempted
        merge_call = call(['git', 'merge', '--no-ff', 'bugfix-branch'])
        self.assertNotIn(merge_call, mock_run_command.call_args_list)


    @patch('studio.review_agent.get_open_prs')
    @patch('studio.review_agent.run_command')
    @patch('builtins.open', new_callable=unittest.mock.mock_open)
    def test_handles_test_success_correctly(self, mock_open, mock_run_command, mock_get_open_prs):
        """
        Ensures that on test success, it merges the PR to main and does NOT write to history.
        """
        # Arrange
        mock_get_open_prs.return_value = [create_mock_pr(102, 'feature-branch', datetime.datetime.now())]
        mock_run_command.return_value = (0, "Success", "")
        agent = ReviewAgent()

        # Act
        agent.run()

        # Assert
        # 1. Verify that the history file was NOT written to
        handle = mock_open()
        handle.write.assert_not_called()

        # 2. Verify the correct git merge sequence was called
        expected_calls = [
            call(['git', 'checkout', 'feature-branch']),
            call(['pytest']),
            call(['git', 'checkout', 'main']),
            call(['git', 'merge', '--no-ff', 'feature-branch']),
            call(['git', 'push', 'origin', 'main']),
        ]
        mock_run_command.assert_has_calls(expected_calls, any_order=False)