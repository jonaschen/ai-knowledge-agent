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
        self.assertEqual(architect.review_history, "History Content")

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
            self.assertEqual(call_args['review_history'], "History Content")
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

if __name__ == "__main__":
    unittest.main()


import tempfile

class TestArchitectMemory(unittest.TestCase):

    def setUp(self):
        # Create temporary knowledge base files
        self.temp_dir = tempfile.TemporaryDirectory()
        self.rules_path = os.path.join(self.temp_dir.name, "rules.md")
        self.history_path = os.path.join(self.temp_dir.name, "review_history.md")

        with open(self.rules_path, "w") as f:
            f.write("# Universal Rule 1\n- Do not mock Pydantic models.")

        with open(self.history_path, "w") as f:
            f.write("## [PR #92] Failure\n- Root Cause: FileNotFoundError")

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('studio.architect.ChatVertexAI')
    @patch("studio.architect.Github")
    @patch("os.getenv")
    def test_init_raises_error_if_files_missing(self, mock_getenv, mock_github, mock_chat_model):
        """
        Ensures the Architect constructor fails if memory files don't exist.
        """
        mock_getenv.return_value = "fake_token"

        file_map = {
            self.rules_path: "# Universal Rule 1\n- Do not mock Pydantic models.",
            self.history_path: "## [PR #92] Failure\n- Root Cause: FileNotFoundError",
            "AGENTS.md": "mock constitution"
        }

        def open_side_effect(path, mode='r'):
            if path in file_map:
                return mock_open(read_data=file_map[path])()
            raise FileNotFoundError(f"[Mock] File not found: {path}")

        with patch("builtins.open", side_effect=open_side_effect):
            with self.assertRaises(FileNotFoundError):
                Architect(repo_name="test/repo", rules_path="non_existent_rules.md", history_path=self.history_path)

            with self.assertRaises(FileNotFoundError):
                Architect(repo_name="test/repo", rules_path=self.rules_path, history_path="non_existent_history.md")

    @patch('studio.architect.StrOutputParser')
    @patch('studio.architect.ChatPromptTemplate')
    @patch('studio.architect.ChatVertexAI')
    @patch("studio.architect.Github")
    @patch("os.getenv")
    def test_plan_feature_injects_knowledge_base_into_prompt(self, mock_getenv, mock_github, mock_chat_model, mock_prompt_cls, mock_parser_cls):
        """
        Verifies that rules.md and review_history.md are loaded and
        injected into the system prompt for the LLM.
        """
        # Arrange
        mock_getenv.return_value = "fake_token"

        mock_chain = MagicMock()
        # Mock the entire chain: prompt | llm | parser -> mock_chain
        mock_prompt_cls.from_template.return_value.__or__.return_value.__or__.return_value = mock_chain

        # Mock file system reads to provide specific content for each file
        file_map = {
            self.rules_path: "# Universal Rule 1\n- Do not mock Pydantic models.",
            self.history_path: "## [PR #92] Failure\n- Root Cause: FileNotFoundError",
            "AGENTS.md": "mock constitution"
        }

        def open_side_effect(path, mode='r'):
            if path in file_map:
                return mock_open(read_data=file_map[path])()
            raise FileNotFoundError(f"[Mock] File not found: {path}")

        with patch("builtins.open", side_effect=open_side_effect):
            architect = Architect(repo_name="test/repo", rules_path=self.rules_path, history_path=self.history_path)

        user_request = "Create a new component."

        # Act
        architect.plan_feature(user_request)

        # Assert: Check the prompt template content
        template_call_args, _ = mock_prompt_cls.from_template.call_args
        system_prompt = template_call_args[0]

        self.assertIn("=== KNOWLEDGE BASE ===", system_prompt)
        self.assertIn("Before generating the Issue, cross-reference the User Request with the Knowledge Base.", system_prompt)
        self.assertIn("If a known anti-pattern is detected", system_prompt)

        # Assert: Check the data passed to the chain's invoke method
        mock_chain.invoke.assert_called_once()
        call_args, _ = mock_chain.invoke.call_args
        invoked_payload = call_args[0]

        self.assertIn("Universal Rule 1", invoked_payload['rules'])
        self.assertIn("Do not mock Pydantic models.", invoked_payload['rules'])
        self.assertIn("[PR #92] Failure", invoked_payload['review_history'])
        self.assertIn("Root Cause: FileNotFoundError", invoked_payload['review_history'])
        self.assertEqual(user_request, invoked_payload['request'])
