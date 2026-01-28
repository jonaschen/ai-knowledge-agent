import os
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

# Load environment variables from .env file
load_dotenv()

# Import dependencies for the new health check feature
from product.main import run_pipeline
# The manager import is moved inside the function to avoid circular dependency
# from studio.manager import receive_quality_report

class ProductManager:
    """
    High-level planner. Generates execution plans in JSON format.
    """
    def __init__(self):
        """Initializes the ProductManager with the standardized LLM wrapper."""
        self.llm = ChatVertexAI(model_name="gemini-2.5-pro", max_output_tokens=8192)
        # You may need to define a prompt and parser as well
        # This is a sample structure
        self.prompt = ChatPromptTemplate.from_template(
            "Generate a JSON execution plan for the following requirement: {requirement}"
        )
        self.parser = JsonOutputParser()
        self.chain = self.prompt | self.llm | self.parser

    def generate_plan(self, requirement: str) -> dict:
        """
        Generates a structured execution plan using the LangChain wrapper.

        Args:
            requirement: The user requirement string.

        Returns:
            A dictionary representing the JSON execution plan.
        """
        return self.chain.invoke({"requirement": requirement})

def run_and_evaluate_pipeline():
    """
    Runs the full product pipeline, evaluates the output quality,
    and reports the score to the Manager.
    This is a module-level function to be called by the Manager's health check.
    """
    # A default topic for the health check run, as seen in manager's original health check
    topic = "AI Agents"
    print(f"PM is running the pipeline for health check on topic: {topic}")

    pipeline_output = run_pipeline(topic)

    # Late import to prevent circular dependency
    from studio.manager import receive_quality_report

    if pipeline_output:
        # Simple quality evaluation: use the confidence score from the pipeline output
        quality_score = pipeline_output.confidence
        print(f"Pipeline output confidence score: {quality_score}")
        receive_quality_report(quality_score)
    else:
        # If the pipeline fails and returns None, report a failure score
        print("PM received no output from the pipeline. Reporting failure score.")
        receive_quality_report(0.0)
