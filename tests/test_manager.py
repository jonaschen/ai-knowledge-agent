import unittest
from unittest.mock import patch, call, mock_open
import time
import sys
import os

from studio.manager import ManagerAgent
from product import main as product_main

# this import will fail until check_run_artifacts is implemented in studio/manager.py
from studio.manager import check_run_artifacts

class TestManagerHealthCheck(unittest.TestCase):

    def setUp(self):
        # Reset the last_check_time before each test
        self.manager = ManagerAgent()
        self.manager.last_check_time = 0.0

    @patch('product.main.run')
    @patch('time.time')
    @patch('subprocess.run')
    def test_health_check_runs_after_one_hour(self, mock_subprocess, mock_time, mock_product_run):
        """Verify the health check is triggered after 3600 seconds."""
        # Initial state: t=0
        mock_time.return_value = 0.0
        self.manager.last_check_time = 0.0 # Set initial time
        self.manager.autopilot_loop(run_once=True)
        mock_product_run.assert_not_called()

        # After 3601 seconds
        mock_time.return_value = 3601.0
        self.manager.autopilot_loop(run_once=True)
        mock_product_run.assert_called_once_with(topic='AI Agents')

    @patch('product.main.run')
    @patch('subprocess.run')
    def test_health_check_runs_immediately_with_cli_flag(self, mock_subprocess, mock_product_run):
        """Verify '--run-now' flag triggers the health check immediately."""
        with patch.object(sys, 'argv', ['studio/manager.py', '--run-now']):
            self.manager.autopilot_loop(run_once=True)
            mock_product_run.assert_called_once_with(topic='AI Agents')

    @patch('product.main.run')
    @patch('time.time')
    @patch('subprocess.run')
    def test_health_check_does_not_run_on_normal_loop(self, mock_subprocess, mock_time, mock_product_run):
        """Verify the health check is NOT triggered on a normal loop cycle."""
        mock_time.return_value = 100.0
        with patch.object(sys, 'argv', ['studio/manager.py']):
             self.manager.autopilot_loop(run_once=True)
             mock_product_run.assert_not_called()

class TestManagerHealthChecks(unittest.TestCase):

    def test_health_check_success(self):
        """
        GIVEN a successful run with an MP3 and a clean log
        WHEN the manager checks the artifacts
        THEN it should return a healthy status
        """
        mp3_path = "output/test_run.mp3"
        log_path = "output/test_run.log"
        log_content = "INFO: Pipeline started.\nINFO: Broadcaster completed.\nINFO: Pipeline completed successfully."

        with patch('os.path.exists') as mock_exists, \
             patch('builtins.open', mock_open(read_data=log_content)) as mock_file:

            # Configure the mock to return True for both files
            mock_exists.side_effect = lambda path: path in [mp3_path, log_path]

            is_healthy, reason = check_run_artifacts(log_path, mp3_path)

            self.assertTrue(is_healthy)
            self.assertEqual(reason, "Artifacts verified successfully.")

    def test_health_check_fails_on_missing_mp3(self):
        """
        GIVEN a run where the output MP3 is missing
        WHEN the manager checks the artifacts
        THEN it should return an unhealthy status
        """
        mp3_path = "output/test_run.mp3"
        log_path = "output/test_run.log"

        with patch('os.path.exists') as mock_exists:
            # Configure the mock to return False for the mp3
            mock_exists.side_effect = lambda path: path == log_path

            is_healthy, reason = check_run_artifacts(log_path, mp3_path)

            self.assertFalse(is_healthy)
            self.assertIn("Missing output file", reason)

    def test_health_check_fails_on_error_in_log(self):
        """
        GIVEN a run where the log file contains an error
        WHEN the manager checks the artifacts
        THEN it should return an unhealthy status
        """
        mp3_path = "output/test_run.mp3"
        log_path = "output/test_run.log"
        log_content = "INFO: Pipeline started.\nERROR: Broadcaster failed to generate audio."

        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', mock_open(read_data=log_content)):

            is_healthy, reason = check_run_artifacts(log_path, mp3_path)

            self.assertFalse(is_healthy)
            self.assertIn("Error detected in log file", reason)
