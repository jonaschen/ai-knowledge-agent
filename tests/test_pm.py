import unittest
from unittest.mock import patch, MagicMock, mock_open
from langchain_core.messages import AIMessage
from studio.pm import ProductManager
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

class TestProductManager(unittest.TestCase):

    @patch('studio.pm.ChatVertexAI')
    @patch('builtins.open', new_callable=mock_open, read_data="# AI Software Studio Constitution")
    def test_initialization_and_model_usage(self, mock_file, mock_chat_vertex_ai):
        """
        Tests that the ProductManager initializes correctly, loads the constitution,
        and uses the specified ChatVertexAI model and output parser.
        """
        # Arrange
        mock_llm_instance = MagicMock()
        # Mock a valid JSON response matching the new expected structure
        expected_json = '''
        {
            "product_intent": "Solve X",
            "output_contract": "Report Y",
            "quality_criteria": ["Criteria 1"],
            "steps": [
                {
                    "name": "Step 1",
                    "description": "Do Z",
                    "acceptance_criteria": ["Done Z"]
                }
            ]
        }
        '''
        success_message = AIMessage(content=expected_json)
        mock_llm_instance.invoke.return_value = success_message
        mock_llm_instance.return_value = success_message
        mock_chat_vertex_ai.return_value = mock_llm_instance

        # Act
        pm = ProductManager()

        # Assert - Constitution loaded
        mock_file.assert_called_with("AGENTS.md", "r")

        # Assert - LLM Model
        mock_chat_vertex_ai.assert_called_once_with(
            model_name='gemini-2.5-pro',
            max_output_tokens=8192
        )

        # Assert - Parser configuration
        # We expect pydantic_object to be set to enforce structure
        self.assertIsInstance(pm.parser, JsonOutputParser)
        self.assertIsNotNone(pm.parser.pydantic_object, "Parser should have a pydantic_object defined")
        self.assertEqual(pm.parser.pydantic_object.__name__, 'ExecutionPlan')

        # Assert - Prompt configuration
        # Check that the prompt expects 'constitution'
        self.assertIn("constitution", pm.prompt.input_variables)

        # Act - Generate Plan
        # We allow the chain to run. The LLM is mocked to return the JSON.
        plan = pm.generate_plan("Test Requirement")

        # Assert - Verify LLM was invoked with prompt containing constitution
        # Retrieve the arguments passed to llm.invoke
        self.assertTrue(mock_llm_instance.invoke.called or mock_llm_instance.called)

        if mock_llm_instance.invoke.called:
             args = mock_llm_instance.invoke.call_args[0]
        else:
             args = mock_llm_instance.call_args[0]

        llm_input = args[0]

        # If input is list of messages
        if isinstance(llm_input, list):
            content = "".join([m.content for m in llm_input])
        # If input is PromptValue
        elif hasattr(llm_input, 'to_messages'):
            content = "".join([m.content for m in llm_input.to_messages()])
        else:
            # Fallback assuming it might be a string (unlikely for ChatModel but possible if passed direct string)
            content = str(llm_input)

        self.assertIn("# AI Software Studio Constitution", content)
        self.assertIn("Test Requirement", content)

        # Verify return value is the parsed dict
        self.assertEqual(plan['product_intent'], "Solve X")

    @patch('studio.pm.ChatVertexAI')
    def test_llm_initialization_with_correct_parameters(self, mock_chat_vertex_ai):
        """
        Test that ProductManager initializes ChatVertexAI with the correct arguments.
        This test is the specification for the fix.
        """
        # Arrange: We expect ChatVertexAI to be called with specific arguments.
        mock_llm_instance = MagicMock()
        mock_chat_vertex_ai.return_value = mock_llm_instance

        # Act: Instantiate the ProductManager, which should trigger the LLM setup.
        pm = ProductManager()

        # Assert: Verify that ChatVertexAI was called exactly once with the correct
        # model_name and max_output_tokens arguments.
        mock_chat_vertex_ai.assert_called_once_with(
            model_name='gemini-2.5-pro',
            max_output_tokens=8192
        )
        self.assertEqual(pm.llm, mock_llm_instance)


if __name__ == '__main__':
    unittest.main()
