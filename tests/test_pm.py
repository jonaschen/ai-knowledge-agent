import pytest
import json
from studio.pm import ProductManager

def test_pm_creates_structured_plan():
    """
    Verify the ProductManager can take a high-level goal and produce
    a structured JSON plan with the required fields.
    """
    # Arrange
    pm = ProductManager()
    user_goal = "Produce a deep dive on the impact of Generative AI on software development."

    # Act
    plan_json = pm.create_plan(user_goal)
    plan = json.loads(plan_json) # Ensures output is valid JSON

    # Assert
    assert "topic" in plan
    assert "target_audience" in plan
    assert "key_questions" in plan
    assert isinstance(plan["key_questions"], list)
    assert plan["topic"] == user_goal # For now, the topic can be the goal itself.

def test_pm_handles_empty_input():
    """
    Curator-style robustness test.
    Verify the agent fails gracefully with invalid input.
    """
    # Arrange
    pm = ProductManager()

    # Act & Assert
    with pytest.raises(ValueError, match="User goal cannot be empty."):
        pm.create_plan("")

    with pytest.raises(ValueError, match="User goal cannot be empty."):
        pm.create_plan(None)
