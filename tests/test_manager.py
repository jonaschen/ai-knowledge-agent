import unittest
from unittest.mock import patch, call
import time
import sys

from studio.manager import ManagerAgent
from product import main as product_main

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
