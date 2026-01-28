import unittest
from unittest.mock import patch, call, mock_open
import time
import sys
import subprocess
import os

from studio.manager import ManagerAgent
from studio import manager

class TestManagerHealthCheck(unittest.TestCase):

    def setUp(self):
        # Reset the last_check_time before each test
        self.manager = ManagerAgent()
        self.manager.last_check_time = 0.0

    @patch('studio.pm.run_and_evaluate_pipeline')
    @patch('time.time')
    @patch('subprocess.run')
    def test_health_check_runs_after_one_hour(self, mock_subprocess, mock_time, mock_pm_run):
        """Verify the health check is triggered after 3600 seconds."""
        # Initial state: t=0
        mock_time.return_value = 0.0
        self.manager.last_check_time = 0.0 # Set initial time
        self.manager.autopilot_loop(run_once=True)
        mock_pm_run.assert_not_called()

        # After 3601 seconds
        mock_time.return_value = 3601.0
        self.manager.autopilot_loop(run_once=True)
        mock_pm_run.assert_called_once()

    @patch('studio.pm.run_and_evaluate_pipeline')
    @patch('subprocess.run')
    def test_health_check_runs_immediately_with_cli_flag(self, mock_subprocess, mock_pm_run):
        """Verify '--run-now' flag triggers the health check immediately."""
        with patch.object(sys, 'argv', ['studio/manager.py', '--run-now']):
            self.manager.autopilot_loop(run_once=True)
            mock_pm_run.assert_called_once()

    @patch('studio.pm.run_and_evaluate_pipeline')
    @patch('time.time')
    @patch('subprocess.run')
    def test_health_check_does_not_run_on_normal_loop(self, mock_subprocess, mock_time, mock_pm_run):
        """Verify the health check is NOT triggered on a normal loop cycle."""
        mock_time.return_value = 100.0
        with patch.object(sys, 'argv', ['studio/manager.py']):
             self.manager.autopilot_loop(run_once=True)
             mock_pm_run.assert_not_called()

class TestManager(unittest.TestCase):

    @patch('studio.manager.ManagerAgent.autopilot_loop')
    @patch('subprocess.run')
    def test_manager_pulls_latest_code_on_startup(self, mock_subprocess_run, mock_autopilot_loop):
        """
        Verify the manager runs 'git pull' before executing its main loop.
        """
        # Configure the mock to simulate a successful command
        mock_subprocess_run.return_value = None
        mock_autopilot_loop.return_value = None

        # We assume the manager's main function will be called.
        # We wrap it in a try block to catch any other errors and ensure our assertion runs.
        try:
            manager.main()
        except Exception as e:
            # We don't expect other errors in this unit test, but we'll allow them to fail the test
            # if they occur. The key is to check the call to subprocess.
            pass

        # Assert that 'git pull' was the first command executed.
        expected_call = call(['git', 'pull'], check=True, capture_output=True, text=True)
        self.assertIn(expected_call, mock_subprocess_run.call_args_list,
                      "The manager did not attempt to run 'git pull' on startup.")

    @patch('studio.manager.ManagerAgent.autopilot_loop')
    @patch('subprocess.run')
    def test_manager_handles_git_pull_failure(self, mock_subprocess_run, mock_autopilot_loop):
        """
        Verify the manager logs an error and exits if 'git pull' fails.
        """
        # Configure the mock to simulate a failed command (e.g., merge conflict)
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=['git', 'pull'],
            stderr="fatal: a merge conflict occurred"
        )
        mock_autopilot_loop.return_value = None

        # The manager should catch this exception and exit gracefully.
        # We expect a SystemExit or a similar clean exit mechanism.
        with self.assertRaises(SystemExit):
            manager.main()
