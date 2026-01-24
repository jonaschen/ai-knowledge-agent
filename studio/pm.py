import json

class ProductManager:
    """
    Receives high-level user goals and breaks them down into a
    structured JSON Execution Plan for other agents to consume.
    """
    def create_plan(self, user_goal: str) -> str:
        """
        Generates a structured JSON plan from a user goal.

        Args:
            user_goal: A string describing the desired output.

        Returns:
            A JSON string representing the execution plan.

        Raises:
            ValueError: If the user_goal is null or empty.
        """
        if not user_goal:
            raise ValueError("User goal cannot be empty.")

        # This is a stub implementation to satisfy the initial test.
        # Future work will involve more sophisticated parsing/generation.
        plan = {
            "topic": user_goal,
            "target_audience": "Technical professionals", # Placeholder
            "key_questions": [ # Placeholder
                "What is the core technology?",
                "What are the primary use cases?",
                "What are the known limitations and risks?"
            ],
            "tasks": { # Structure for future tasks
                "curator": [],
                "researcher": [],
                "analyst": []
            }
        }

        return json.dumps(plan, indent=2)
