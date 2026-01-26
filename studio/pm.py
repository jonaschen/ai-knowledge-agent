# studio/pm.py
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List

# --- Abstractions (Dependency Inversion Principle) ---

class PlanningStrategy(ABC):
    """Abstract base class for different planning strategies."""
    @abstractmethod
    def create_plan(self, goal: str) -> Dict[str, Any]:
        pass

class PlanStorage(ABC):
    """Abstract base class for storing the generated plan."""
    @abstractmethod
    def save(self, plan: Dict[str, Any]):
        pass

# --- Concrete Implementations ---

class DefaultPlanningStrategy(PlanningStrategy):
    """
    A basic strategy that breaks a goal into standard TDD-based tasks.
    """
    def create_plan(self, goal: str) -> Dict[str, Any]:
        # This is where the original planning logic goes.
        # For now, a simple placeholder will suffice.
        tasks = [
            {"id": 1, "title": "Create Failing Test (TDD) for: " + goal, "status": "pending"},
            {"id": 2, "title": "Implement Code to Pass Test for: " + goal, "status": "pending"},
            {"id": 3, "title": "Refactor and Verify for: " + goal, "status": "pending"},
        ]
        return {"goal": goal, "tasks": tasks}

class JsonPlanStorage(PlanStorage):
    """Saves the plan to a JSON file."""
    def __init__(self, filepath: str):
        self.filepath = filepath

    def save(self, plan: Dict[str, Any]):
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(plan, f, indent=4)
        print(f"Plan saved to {self.filepath}")

# --- Orchestrator (Single Responsibility Principle) ---

class ProductManager:
    """
    Orchestrates plan generation and storage by delegating to strategy and storage objects.
    """
    def __init__(self, strategy: PlanningStrategy, storage: PlanStorage):
        self._strategy = strategy
        self._storage = storage

    def execute(self, high_level_goal: str):
        """Generates and saves a plan for a given goal."""
        print(f"PM: Generating plan for goal '{high_level_goal}'...")
        plan = self._strategy.create_plan(high_level_goal)
        self._storage.save(plan)
        print("PM: Plan generation complete.")

# Example usage, can be placed in a main block or another script
if __name__ == '__main__':
    # This demonstrates how the decoupled components are assembled
    goal = "Refactor the Curator to use a new API."

    # 1. Choose a strategy
    planning_strategy = DefaultPlanningStrategy()

    # 2. Choose a storage method
    plan_storage = JsonPlanStorage(filepath="execution_plan.json")

    # 3. Inject dependencies into the orchestrator
    pm = ProductManager(strategy=planning_strategy, storage=plan_storage)

    # 4. Execute
    pm.execute(goal)
