import unittest
import subprocess
import json
from unittest.mock import patch, MagicMock

class TestProductManager(unittest.TestCase):

    @patch('studio.pm.ChatVertexAI')
    @patch('studio.pm.dotenv.load_dotenv')
    def test_pm_cli_generates_valid_plan(self, mock_load_dotenv, mock_ChatVertexAI):
        """
        Tests if the PM agent can be run via CLI and produces a valid JSON plan.
        """
        # --- Arrange ---
        # 1. Mock the .env loading
        mock_load_dotenv.return_value = True

        # 2. Mock the Vertex AI client and its response
        mock_model = MagicMock()
        mock_response = MagicMock()

        # This is the expected JSON string the LLM would return
        expected_json_output = {
            "title": "Deep Dive on AI Agents",
            "curator_tasks": [
                {"task_id": "C01", "book_query": "foundational books on software agents"},
                {"task_id": "C02", "book_query": "recent developments in multi-agent systems"}
            ],
            "researcher_tasks": [
                {"task_id": "R01", "query": "history of agent-based computing"},
                {"task_id": "R02", "query": "counter-arguments to agent autonomy"}
            ],
            "analyst_tasks": [
                {"task_id": "A01", "description": "Synthesize themes from C01 and R01 regarding the evolution of agents."}
            ]
        }
        mock_response.text = json.dumps(expected_json_output)
        mock_model.send_message.return_value = mock_response
        mock_ChatVertexAI.return_value = mock_model

        # 3. Define the command to run
        goal = "Deep dive on AI Agents"
        command = ["python", "-m", "studio.pm", goal]

        # --- Act ---
        # Run the pm.py script as a separate process
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # --- Assert ---
        # 1. Check that .env was loaded
        mock_load_dotenv.assert_called_once()

        # 2. Check that the CLI output is valid JSON
        try:
            output_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail("CLI output is not valid JSON.")

        # 3. Check that the model was initialized and called correctly
        mock_ChatVertexAI.assert_called_once_with(model="gemini-1.5-pro")
        mock_model.send_message.assert_called_once()

        # 4. Check the structure and content of the parsed JSON
        self.assertIn("title", output_data)
        self.assertIn("curator_tasks", output_data)
        self.assertIn("researcher_tasks", output_data)
        self.assertIn("analyst_tasks", output_data)
        self.assertEqual(len(output_data["curator_tasks"]), 2)
        self.assertEqual(output_data["title"], "Deep Dive on AI Agents")

if __name__ == '__main__':
    unittest.main()