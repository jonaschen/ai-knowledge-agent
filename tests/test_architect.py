import unittest
from unittest.mock import patch, mock_open, MagicMock
from studio.architect import Architect

class TestArchitectMemory(unittest.TestCase):

    @patch('studio.architect.ChatVertexAI')
    @patch('studio.architect.Github')
    @patch('os.getenv')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.path.exists')
    def test_plan_feature_includes_memory_files(self, mock_exists, mock_file, mock_getenv, mock_github, mock_chat_vertex_ai):
        # Arrange
        mock_getenv.return_value = 'dummy_token'
        mock_github.return_value.get_repo.return_value = MagicMock()

        def side_effect(path, mode='r'):
            if 'rules.md' in path:
                return mock_open(read_data='## Universal Rule\n- Always use absolute imports.\n')()
            elif 'review_history.md' in path:
                return mock_open(read_data='## [PR #123] API Timeout\n- Fix Pattern: Implement exponential backoff.\n')()
            elif 'AGENTS.md' in path:
                return mock_open(read_data='AGENTS.md content')()
            return mock_open(read_data='default content')()

        mock_file.side_effect = side_effect
        mock_exists.return_value = True

        architect = Architect(repo_name="test/repo")

        # We need to capture the prompt string that is created
        with patch('langchain_core.prompts.ChatPromptTemplate.from_template') as mock_from_template:
            mock_prompt = MagicMock()
            mock_chain = MagicMock()
            mock_from_template.return_value = mock_prompt
            mock_prompt.__or__.return_value = mock_chain
            mock_chain.__or__.return_value = mock_chain

            # Act
            architect.plan_feature("New feature request")

            # Assert
            self.assertTrue(mock_from_template.called)
            prompt_string = mock_from_template.call_args[0][0]

            self.assertIn("=== YOUR CONSTITUTION (AGENTS.md) ===", prompt_string)
            self.assertIn("{constitution}", prompt_string)
            self.assertIn("=== DESIGN PATTERNS (MUST FOLLOW) ===", prompt_string)
            self.assertIn("{rules}", prompt_string)
            self.assertIn("=== RECENT FAILURES (AVOID THESE) ===", prompt_string)
            self.assertIn("{history}", prompt_string)
            self.assertIn("=== USER REQUEST ===", prompt_string)
            self.assertIn("{request}", prompt_string)

if __name__ == '__main__':
    unittest.main()
