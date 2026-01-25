# tests/test_architect_memory.py
import unittest
from unittest.mock import patch, mock_open

# This import will resolve once the project structure is correct
from studio.architect import Architect

class TestArchitectMemory(unittest.TestCase):

    @patch('studio.architect.ChatVertexAI')
    @patch('studio.architect.Github')
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'test_token'})
    def test_architect_incorporates_studio_memory(self, mock_github, mock_vertexai):
        """
        VERIFIES: The Architect loads and uses rules.md and review_history.md.

        This test ensures that the Architect correctly reads its memory files
        during initialization and injects their content into the planning prompt.
        """
        # 1. Define mock file contents
        constitution_content = "AGENTS.md content"
        rules_content = "## Universal Rule\n- Follow TDD."
        history_content = "## [PR #456] Failure\n- Forgot to mock."

        # 2. Setup mock_open to simulate reading these files
        mock_file_map = {
            'AGENTS.md': mock_open(read_data=constitution_content).return_value,
            'studio/rules.md': mock_open(read_data=rules_content).return_value,
            'studio/review_history.md': mock_open(read_data=history_content).return_value,
        }

        # The patch intercepts any 'open' call.
        m = mock_open()
        m.side_effect = lambda f, *args, **kwargs: mock_file_map.get(f, mock_open(read_data='').return_value)

        with patch('builtins.open', m):
            # Instantiate the Architect with a dummy repo name
            architect = Architect(repo_name="test/repo")

            # This test will fail until __init__ is updated
            self.assertEqual(architect.rules, rules_content)
            self.assertEqual(architect.history, history_content)

            # Generate the prompt. Before the fix, this prompt will be missing sections.
            prompt = architect._create_planning_prompt("Test user request")

            # Assert the prompt contains the memory
            self.assertIn("=== DESIGN PATTERNS (MUST FOLLOW) ===", prompt)
            self.assertIn(rules_content, prompt)
            self.assertIn("=== RECENT FAILURES (AVOID THESE) ===", prompt)
            self.assertIn(history_content, prompt)
            self.assertIn(constitution_content, prompt) # Ensure old logic isn't broken
            self.assertIn("Test user request", prompt)
