
import unittest
from unittest.mock import MagicMock, patch
from typing import TypedDict, Literal

# Mock needed modules before importing analyst_core
with patch('langchain_google_vertexai.ChatVertexAI') as MockChatVertexAI:
    import analyst_core

class TestReflexionLoop(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        analyst_core.llm = self.mock_llm

    def test_loop_lgtm(self):
        """Test that loop ends when critique returns LGTM"""
        # 1. Router response
        # 2. Draft response
        # 3. Critique response (LGTM)

        # We need to mock the responses in sequence
        self.mock_llm.invoke.side_effect = [
            MagicMock(content="instructional"), # Router
            MagicMock(content="Draft 1"),       # Draft
            MagicMock(content="LGTM"),          # Critique
        ]

        initial_state = {
            "original_text": "Some text",
            "revision_count": 0
        }

        result = analyst_core.app.invoke(initial_state)

        self.assertEqual(result["draft_analysis"], "Draft 1")
        self.assertIn("LGTM", result["critique_feedback"])
        self.assertEqual(self.mock_llm.invoke.call_count, 3)

    def test_loop_revision(self):
        """Test that loop revises when critique is negative"""
        # 1. Router
        # 2. Draft
        # 3. Critique (Bad)
        # 4. Revise
        # 5. Critique (LGTM)

        self.mock_llm.invoke.side_effect = [
            MagicMock(content="instructional"), # Router
            MagicMock(content="Draft 1"),       # Draft
            MagicMock(content="Please improve"),# Critique 1
            MagicMock(content="Draft 2"),       # Revise 1
            MagicMock(content="LGTM"),          # Critique 2
        ]

        initial_state = {
            "original_text": "Some text",
            "revision_count": 0
        }

        result = analyst_core.app.invoke(initial_state)

        self.assertEqual(result["draft_analysis"], "Draft 2")
        self.assertIn("LGTM", result["critique_feedback"])
        self.assertEqual(result["revision_count"], 2) # draft=1, revise=2
        self.assertEqual(self.mock_llm.invoke.call_count, 5)

    def test_max_retries(self):
        """Test that loop stops after max retries"""
        # 1. Router
        # 2. Draft (count=1)
        # 3. Critique (Bad)
        # 4. Revise (count=2)
        # 5. Critique (Bad)
        # 6. Revise (count=3)
        # 7. Critique (Bad) -> Stop

        self.mock_llm.invoke.side_effect = [
            MagicMock(content="instructional"),
            MagicMock(content="Draft 1"),
            MagicMock(content="Bad"),
            MagicMock(content="Draft 2"),
            MagicMock(content="Bad"),
            MagicMock(content="Draft 3"),
            MagicMock(content="Bad"),
        ]

        initial_state = {
            "original_text": "Some text",
            "revision_count": 0
        }

        result = analyst_core.app.invoke(initial_state)

        self.assertEqual(result["draft_analysis"], "Draft 3")
        self.assertEqual(result["revision_count"], 3)
        self.assertEqual(self.mock_llm.invoke.call_count, 7)

if __name__ == '__main__':
    unittest.main()
