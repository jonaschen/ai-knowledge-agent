import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
from studio.architect import Architect
from langchain_core.messages import AIMessage


class TestArchitect(unittest.TestCase):
    @patch("studio.architect.Github")
    @patch("studio.architect.ChatVertexAI")
    @patch("os.getenv")
    @patch("builtins.open", new_callable=mock_open)
    def test_init_loads_memories(self, mock_file, mock_getenv, mock_vertex, mock_github):
        # Setup mocks
        mock_getenv.return_value = "fake_token"

        # Setup file contents
        file_contents = {
            "AGENTS.md": "Constitution Content",
            "studio/rules.md": "Rules Content",
            "studio/review_history.md": "History Content"
        }

        def side_effect(file, *args, **kwargs):
            content = file_contents.get(file, "")
            # Create a new mock for each file to support context manager
            file_mock = MagicMock()
            file_mock.__enter__.return_value = file_mock
            file_mock.__exit__.return_value = None
            file_mock.read.return_value = content
            return file_mock

        mock_file.side_effect = side_effect

        architect = Architect("test_repo")

        self.assertEqual(architect.constitution, "Constitution Content")
        self.assertEqual(architect.rules, "Rules Content")
        self.assertEqual(architect.history, "History Content")

    @patch("studio.architect.Github")
    @patch("studio.architect.ChatVertexAI")
    @patch("os.getenv")
    @patch("builtins.open", new_callable=mock_open)
    def test_plan_feature_includes_memories(self, mock_file, mock_getenv, mock_vertex, mock_github):
        # Setup mocks
        mock_getenv.return_value = "fake_token"

        file_contents = {
            "AGENTS.md": "Constitution Content",
            "studio/rules.md": "Rules Content",
            "studio/review_history.md": "History Content"
        }

        def side_effect(file, *args, **kwargs):
            content = file_contents.get(file, "")
            file_mock = MagicMock()
            file_mock.__enter__.return_value = file_mock
            file_mock.__exit__.return_value = None
            file_mock.read.return_value = content
            return file_mock

        mock_file.side_effect = side_effect

        # Mock ChatPromptTemplate to verify chain invocation
        with patch("studio.architect.ChatPromptTemplate") as mock_prompt_cls:
            mock_chain = MagicMock()
            # prompt | llm | parser -> mock_chain
            mock_prompt_cls.from_template.return_value.__or__.return_value.__or__.return_value = mock_chain

            architect = Architect("test_repo")
            architect.plan_feature("Test Request")

            # Verify invoke was called with correct context
            mock_chain.invoke.assert_called_once()
            call_args = mock_chain.invoke.call_args[0][0]

            self.assertEqual(call_args['constitution'], "Constitution Content")
            self.assertEqual(call_args['rules'], "Rules Content")
            self.assertEqual(call_args['history'], "History Content")
            self.assertEqual(call_args['request'], "Test Request")

    @patch("studio.architect.Github")
    @patch("studio.architect.ChatVertexAI")
    @patch("os.getenv")
    @patch("builtins.open", new_callable=mock_open)
    def test_plan_feature_distinguishes_teams(self, mock_file, mock_getenv, mock_vertex, mock_github):
        # Setup mocks
        mock_getenv.return_value = "fake_token"

        # Setup file contents (minimal)
        file_contents = {
            "AGENTS.md": "Constitution",
            "studio/rules.md": "Rules",
            "studio/review_history.md": "History"
        }

        def side_effect(file, *args, **kwargs):
            content = file_contents.get(file, "")
            file_mock = MagicMock()
            file_mock.__enter__.return_value = file_mock
            file_mock.__exit__.return_value = None
            file_mock.read.return_value = content
            return file_mock

        mock_file.side_effect = side_effect

        with patch("studio.architect.ChatPromptTemplate") as mock_prompt_cls:
            mock_chain = MagicMock()
            mock_prompt_cls.from_template.return_value.__or__.return_value.__or__.return_value = mock_chain

            architect = Architect("test_repo")
            architect.plan_feature("New Feature")

            # Check prompt content
            args, _ = mock_prompt_cls.from_template.call_args
            template_str = args[0]

            # Assertions for team awareness
            self.assertIn("=== TEAM STRUCTURE ===", template_str)
            self.assertIn("1. Studio Team", template_str)
            self.assertIn("2. Product Team", template_str)
            self.assertIn("determine which team is responsible", template_str)
            self.assertIn("Title: [Team Name]", template_str)

    @patch('studio.architect.Github')
    @patch('studio.architect.ChatVertexAI')
    @patch('studio.architect.os.getenv')
    def test_handles_missing_knowledge_files_gracefully(self, mock_getenv, mock_chat_vertex_ai, mock_github):
        """
        Verify Architect defaults to empty strings if knowledge files are not found.
        """
        # Mock os.getenv to return a dummy token
        mock_getenv.return_value = "dummy_token"

        # Mock 'open' to only find AGENTS.md and raise FileNotFoundError for others
        def open_side_effect(file_path, mode='r'):
            if file_path == 'AGENTS.md':
                return mock_open(read_data="Constitution content").return_value
            else:
                raise FileNotFoundError

        with patch('builtins.open', side_effect=open_side_effect):
            architect = Architect("test/repo")
            # Assert that attributes default to empty strings on failure
            self.assertEqual(architect.rules, "")
            self.assertEqual(architect.history, "")

if __name__ == "__main__":
    unittest.main()
