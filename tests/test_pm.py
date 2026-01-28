import unittest
from unittest.mock import patch, MagicMock

# Assume the final output is a Pydantic model or a simple dict for now
# This is a placeholder for the actual output structure from product/main.py
from pydantic import BaseModel

class PipelineOutput(BaseModel):
    summary: str
    confidence: float

def test_pm_runs_pipeline_and_reports_quality():
    """
    Ensures the PM can trigger the production pipeline, evaluate its output,
    and report the quality score to the Manager.
    """
    # ARRANGE
    # IMPORTANT: Use a concrete instance, NOT MagicMock, for the return value
    # to comply with `rules.md` Pattern 1.1 (Pydantic Mocking).
    mock_pipeline_output = PipelineOutput(summary="This is a test summary.", confidence=0.9)

    # Patch the dependencies: the pipeline itself and the manager's reporting method.
    # We patch `run_pipeline` where it is looked up: in the `studio.pm` module.
    with patch('studio.pm.run_pipeline', return_value=mock_pipeline_output) as mock_run_pipeline, \
         patch('studio.manager.receive_quality_report') as mock_receive_report:

        # Import the agent we are testing
        from studio import pm

        # ACT
        # This is the new function we will create on the PM agent
        pm.run_and_evaluate_pipeline()

        # ASSERT
        # 1. Verify the production pipeline was called
        mock_run_pipeline.assert_called_once()

        # 2. Verify the PM reported a score to the Manager.
        #    The exact score is less important than the fact that the call was made.
        mock_receive_report.assert_called_once()
        # Check that the argument is a float (the quality score)
        args, _ = mock_receive_report.call_args
        assert isinstance(args[0], float)
