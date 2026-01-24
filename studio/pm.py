import os
import sys
import json
import argparse
import dotenv
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel, Part

# Correctly import from the new ChatVertexAI location
from vertexai.language_models import ChatVertexAI


# System Prompt defining the PM's persona and output format.
PM_SYSTEM_PROMPT = """
You are the Product Manager for an AI Software Studio. Your role is to break down high-level user goals into a structured, actionable JSON plan for the 'Deep Context Reader' system.

The user will provide a goal, for example: "A deep dive on the history of Stoicism."

You must generate a JSON object with the following structure:
- "title": A concise, descriptive title for the overall goal.
- "curator_tasks": A list of tasks for the Curator agent. Each task is an object with "task_id" and "book_query" for the Google Books API.
- "researcher_tasks": A list of tasks for the Researcher agent. Each task is an object with "task_id" and a "query" for web searches (e.g., "deep reviews of Meditations", "counter-arguments to Stoic philosophy").
- "analyst_tasks": A list of high-level synthesis tasks for the Analyst agent. Each task is an object with "task_id" and a "description" of what to analyze.

Your plan must be strategic, logical, and directly executable by the other agents. Be specific in your queries.
"""

class ProductManager:
    """
    An agent that breaks down high-level goals into a structured JSON plan.
    """
    def __init__(self):
        """
        Initializes the ProductManager, loading environment variables and setting up the LLM.
        """
        dotenv.load_dotenv()
        # Ensure GOOGLE_APPLICATION_CREDENTIALS is set in .env
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            raise EnvironmentError("GOOGLE_APPLICATION_CREDENTIALS not found in .env file.")

        # Initialize Vertex AI
        project_id = os.getenv("GCP_PROJECT_ID")
        location = os.getenv("GCP_REGION", "us-central1")
        aiplatform.init(project=project_id, location=location)

        self.model = ChatVertexAI(model="gemini-1.5-pro")

    def generate_plan(self, user_goal: str) -> str:
        """
        Generates a structured JSON plan from a user goal using an LLM.

        Args:
            user_goal: The high-level goal from the user.

        Returns:
            A JSON string representing the execution plan.
        """
        chat = self.model.start_chat(
            context=PM_SYSTEM_PROMPT
        )
        response = chat.send_message(f"Generate a plan for this goal: '{user_goal}'")

        # Basic cleanup to extract JSON from markdown code blocks if the LLM wraps it
        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        # Validate that the output is valid JSON before returning
        try:
            json.loads(cleaned_text)
            return cleaned_text
        except json.JSONDecodeError as e:
            print(f"Error: LLM returned invalid JSON. {e}", file=sys.stderr)
            # Return a structured error JSON
            error_payload = {
                "error": "Failed to generate valid plan.",
                "details": str(e),
                "raw_output": response.text
            }
            return json.dumps(error_payload, indent=2)


if __name__ == "__main__":
    """
    CLI entry point for the ProductManager agent.
    """
    parser = argparse.ArgumentParser(description="Generate a project plan from a high-level goal.")
    parser.add_argument("goal", type=str, help="The high-level goal to be planned.")
    args = parser.parse_args()

    pm = ProductManager()
    plan_json = pm.generate_plan(args.goal)
    print(plan_json)
