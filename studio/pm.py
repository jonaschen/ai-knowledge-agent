import os
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class ProductManager:
    """
    High-level planner. Generates execution plans in JSON format.
    """
    def __init__(self):
        """Initializes the ProductManager with the standardized LLM wrapper."""
        load_dotenv()
        self.llm = ChatVertexAI(model="gemini-2.5-pro", temperature=0.0)
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
