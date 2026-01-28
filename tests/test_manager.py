import unittest
from unittest.mock import patch, call
import sys
import time
from studio.manager import ManagerAgent

class TestManagerHealthCheck(unittest.TestCase):

    def setUp(self):
        self.manager = ManagerAgent()

    @patch('product.main.run_deep_context_reader')
    def test_health_check_runs_with_run_now_flag(self, mock_run_pipeline):
        """
        Verify that the health check is triggered immediately when --run-now flag is present.
        """
        # Arrange: Simulate command-line arguments
        test_args = ["manager.py", "--run-now"]
        with patch.object(sys, 'argv', test_args):
            # Act
            self.manager.run_health_check()

            # Assert
            mock_run_pipeline.assert_called_once_with('AI Agents')

    @patch('product.main.run_deep_context_reader')
    @patch('time.time')
    def test_health_check_runs_after_one_hour(self, mock_time, mock_run_pipeline):
        """
        Verify the health check runs on the first call and then again after an hour.
        """
        # Arrange
        last_check_time = 0  # Initialize to ensure first run

        # Act 1: First run
        mock_time.return_value = 1700000000.0 # Initial time
        last_check_time = self.manager.run_health_check(last_check_time=last_check_time)

        # Assert 1
        mock_run_pipeline.assert_called_once_with('AI Agents')
        self.assertEqual(last_check_time, 1700000000.0)

        # Act 2: Run again after 59 minutes (should not trigger)
        mock_time.return_value = 1700000000.0 + (59 * 60)
        last_check_time = self.manager.run_health_check(last_check_time=last_check_time)

        # Assert 2: Still only one call
        mock_run_pipeline.assert_called_once()

        # Act 3: Run again after 61 minutes (should trigger)
        mock_time.return_value = 1700000000.0 + (61 * 60)
        last_check_time = self.manager.run_health_check(last_check_time=last_check_time)

        # Assert 3: Should now have been called twice
        self.assertEqual(mock_run_pipeline.call_count, 2)
        self.assertEqual(last_check_time, 1700000000.0 + (61 * 60))

    @patch('product.main.run_deep_context_reader')
    def test_health_check_does_not_run_without_flag_or_timer(self, mock_run_pipeline):
        """
        Verify that without the flag, the check doesn't run if the timer hasn't expired.
        """
        # Arrange: No CLI flag
        test_args = ["manager.py"]
        with patch.object(sys, 'argv', test_args):
            # Act: Pass a recent time to simulate it's not time yet
            self.manager.run_health_check(last_check_time=time.time())

            # Assert
            mock_run_pipeline.assert_not_called()
