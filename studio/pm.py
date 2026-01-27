import os
from typing import List
from dotenv import load_dotenv
from langchain_google_vertexai import ChatVertexAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

class Step(BaseModel):
    name: str = Field(description="Name of the step")
    description: str = Field(description="Detailed description of what needs to be done")
    acceptance_criteria: List[str] = Field(description="List of criteria to verify this step is complete")

class ExecutionPlan(BaseModel):
    product_intent: str = Field(description="The user problem being addressed and the goal in user terms")
    output_contract: str = Field(description="Specification of what the Product Team is expected to deliver")
    quality_criteria: List[str] = Field(description="Product-level quality criteria")
    steps: List[Step] = Field(description="Ordered list of execution steps")

class ProductManager:
    """
    High-level planner. Generates execution plans in JSON format.
    The PM Agent is the owner of product intent and product quality.
    """
    def __init__(self):
        """Initializes the ProductManager with the standardized LLM wrapper."""
        self.llm = ChatVertexAI(model="gemini-2.5-pro", temperature=0.0)

        # Load Constitution (AGENTS.md)
        try:
            with open("AGENTS.md", "r") as f:
                self.constitution = f.read()
        except FileNotFoundError:
            # Fallback if file not found, though Architect suggests it should exist
            self.constitution = "Focus on reliability and user value."

        self.parser = JsonOutputParser(pydantic_object=ExecutionPlan)

        system_prompt = """
        You are the Product Manager (PM) Agent for an AI Software Studio.

        === YOUR CONSTITUTION (AGENTS.md) ===
        {constitution}
        =====================================

        === ROLE DEFINITION ===
        You are the owner of product intent and product quality.
        You do NOT produce code.
        Your responsibility is to define WHAT meaningful output is and judge whether it delivers real user value.

        === INSTRUCTIONS ===
        Analyze the following requirement and generate a structured execution plan.

        Your plan must include:
        1. Product Intent: Clearly define the user problem and goal.
        2. Output Contract: Specify exactly what the Product Team must deliver.
        3. Quality Criteria: Define how success is judged at the product level.
        4. Execution Steps: A series of actionable steps to achieve the goal.

        {format_instructions}

        Requirement: {requirement}
        """

        self.prompt = ChatPromptTemplate.from_template(
            system_prompt,
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )

        self.chain = self.prompt | self.llm | self.parser

    def generate_plan(self, requirement: str) -> dict:
        """
        Generates a structured execution plan using the LangChain wrapper.

        Args:
            requirement: The user requirement string.

        Returns:
            A dictionary representing the JSON execution plan.
        """
        return self.chain.invoke({
            "requirement": requirement,
            "constitution": self.constitution
        })
