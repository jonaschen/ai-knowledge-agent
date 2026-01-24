# tests/test_studio_integrity.py
import os

def test_pm_agent_exists():
    """
    Verifies the Product Manager agent file exists as per AGENTS.md v2.1.
    This is a constitutional requirement for the studio layer.
    """
    pm_path = 'studio/pm.py'
    assert os.path.exists(pm_path), f"CRITICAL: The PM agent at '{pm_path}' is missing and must be restored."
