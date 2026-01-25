import unittest
from unittest.mock import MagicMock, patch, mock_open
import os
import sys

# Ensure repo root is in path
sys.path.append(os.getcwd())

try:
    from studio.architect import Architect
except ImportError:
    # If studio is not a package, we might need to adjust or it might be that we are running pytest from root
    pass

class TestArchitectKnowledgeManagement(unittest.TestCase):

    @patch("studio.architect.Github")
    @patch("studio.architect.ChatVertexAI")
    @patch("studio.architect.os.getenv")
    def test_knowledge_loaded_and_used(self, mock_getenv, MockChatVertexAI, MockGithub):
        # Setup env
        mock_getenv.side_effect = lambda k, d=None: "dummy_token" if k == "GITHUB_TOKEN" else d

        # Setup file mocks
        file_contents = {
            "AGENTS.md": "Constitution Content",
            "studio/rules.md": "Rule 1: Adhere to DRY.",
            "studio/review_history.md": "Failure 1: Infinite recursion."
        }

        def side_effect(filename, mode='r'):
            if filename in file_contents:
                return mock_open(read_data=file_contents[filename]).return_value
            raise FileNotFoundError(f"File {filename} not found")

        with patch("builtins.open", side_effect=side_effect):
            architect = Architect("test/repo")

            # Verify loaded content
            # We use try/except or just assert depending on what we expect the *unmodified* code to do (it will fail)
            # But the test code should express the *desired* behavior.
            self.assertTrue(hasattr(architect, 'rules'), "Architect should have 'rules' attribute")
            self.assertTrue(hasattr(architect, 'history'), "Architect should have 'history' attribute")
            self.assertEqual(architect.rules, "Rule 1: Adhere to DRY.")
            self.assertEqual(architect.history, "Failure 1: Infinite recursion.")

            # Verify prompt usage
            mock_llm = MockChatVertexAI.return_value

            with patch("studio.architect.ChatPromptTemplate") as MockPrompt:
                mock_template = MagicMock()
                MockPrompt.from_template.return_value = mock_template

                # Mock the chain construction: template | llm | parser
                mock_step1 = MagicMock()
                mock_template.__or__.return_value = mock_step1
                mock_chain = MagicMock()
                mock_step1.__or__.return_value = mock_chain

                mock_chain.invoke.return_value = "Issue Body"

                architect.plan_feature("My Request")

                # Check template string for new sections
                args, _ = MockPrompt.from_template.call_args
                template_str = args[0]
                self.assertIn("=== DESIGN PATTERNS (MUST FOLLOW) ===", template_str)
                self.assertIn("=== RECENT FAILURES (AVOID THESE) ===", template_str)
                self.assertIn("{rules}", template_str)
                self.assertIn("{history}", template_str)

                # Check invoke args
                call_args = mock_chain.invoke.call_args
                self.assertIsNotNone(call_args, "Chain.invoke should be called")
                if call_args:
                    inputs = call_args[0][0]
                    self.assertIn("rules", inputs)
                    self.assertIn("history", inputs)
                    self.assertEqual(inputs["rules"], "Rule 1: Adhere to DRY.")
                    self.assertEqual(inputs["history"], "Failure 1: Infinite recursion.")
