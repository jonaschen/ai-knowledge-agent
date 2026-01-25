
import unittest
from unittest.mock import MagicMock, patch
from typing import TypedDict, Literal

# Mock needed modules before importing analyst_core
with patch('langchain_google_vertexai.ChatVertexAI') as MockChatVertexAI:
    from product import analyst_core

class TestReflexionLoop(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        analyst_core.llm = self.mock_llm

    def test_loop_lgtm(self):
        """Test that loop ends when critique returns LGTM"""
        self.mock_llm.invoke.side_effect = [
            MagicMock(content="instructional"),   # Router
            MagicMock(content="Test Thesis"),      # Draft - Thesis
            MagicMock(content="1. Core Idea"),   # Draft - Core Ideas
            MagicMock(content="Test Evidence"),  # Draft - Evidence
            MagicMock(content="LGTM"),             # Critique
        ]

        initial_state = {"original_text": "Some text", "revision_count": 0}
        result = analyst_core.app.invoke(initial_state)

        expected_draft = "Central Thesis: Test Thesis\n\nCore Idea 1: 1. Core Idea\nSupporting Evidence: Test Evidence"
        self.assertEqual(result["draft_analysis"], expected_draft)
        self.assertIn("LGTM", result["critique_feedback"])
        self.assertEqual(self.mock_llm.invoke.call_count, 5)

    def test_loop_revision(self):
        """Test that loop revises when critique is negative"""
        self.mock_llm.invoke.side_effect = [
            MagicMock(content="instructional"),    # Router
            MagicMock(content="Test Thesis"),       # Draft - Thesis
            MagicMock(content="1. Core Idea"),    # Draft - Core Ideas
            MagicMock(content="Test Evidence"),   # Draft - Evidence
            MagicMock(content="Please improve"), # Critique 1
            MagicMock(content="Revised Draft 2"),   # Revise 1
            MagicMock(content="LGTM"),              # Critique 2
        ]

        initial_state = {"original_text": "Some text", "revision_count": 0}
        result = analyst_core.app.invoke(initial_state)

        self.assertEqual(result["draft_analysis"], "Revised Draft 2")
        self.assertIn("LGTM", result["critique_feedback"])
        self.assertEqual(result["revision_count"], 2)
        self.assertEqual(self.mock_llm.invoke.call_count, 7)

    def test_max_retries(self):
        """Test that loop stops after max retries"""
        self.mock_llm.invoke.side_effect = [
            MagicMock(content="instructional"),   # Router
            MagicMock(content="Test Thesis"),      # Draft - Thesis
            MagicMock(content="1. Core Idea"),   # Draft - Core Ideas
            MagicMock(content="Test Evidence"),  # Draft - Evidence
            MagicMock(content="Bad"),              # Critique 1
            MagicMock(content="Revised Draft 2"),  # Revise 1
            MagicMock(content="Bad"),              # Critique 2
            MagicMock(content="Revised Draft 3"),  # Revise 2
            MagicMock(content="Bad"),              # Critique 3 -> Stop
        ]

        initial_state = {"original_text": "Some text", "revision_count": 0}
        result = analyst_core.app.invoke(initial_state)

        self.assertEqual(result["draft_analysis"], "Revised Draft 3")
        self.assertEqual(result["revision_count"], 3)
        self.assertEqual(self.mock_llm.invoke.call_count, 9)

if __name__ == '__main__':
    unittest.main()
