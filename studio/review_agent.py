import abc
import subprocess
from dataclasses import dataclass

# --- Data Structures ---
@dataclass
class RunResult:
    passed: bool
    output: str

@dataclass
class PolicyResult:
    passed: bool
    message: str

# --- Abstractions (Interfaces) ---
class VCSProvider(abc.ABC):
    @abc.abstractmethod
    def get_open_prs(self) -> list[dict]:
        pass

    @abc.abstractmethod
    def post_comment(self, pr_id: int, comment: str):
        pass

    @abc.abstractmethod
    def merge_pr(self, pr_id: int):
        pass

class TestRunner(abc.ABC):
    @abc.abstractmethod
    def run(self) -> RunResult:
        pass

class Policy(abc.ABC):
    @abc.abstractmethod
    def check(self, pr_data: dict) -> PolicyResult:
        pass

# --- Concrete Implementations ---
# NOTE: For now, these can be simple placeholders. We'll integrate real APIs later.
class GitHubProvider(VCSProvider):
    def get_open_prs(self) -> list[dict]:
        print("Fetching PRs from GitHub...")
        # In a real scenario, this would use the GitHub API
        return []

    def post_comment(self, pr_id: int, comment: str):
        print(f"Posting to PR #{pr_id}: {comment}")

    def merge_pr(self, pr_id: int):
        print(f"Merging PR #{pr_id}")

class PytestRunner(TestRunner):
    def run(self) -> RunResult:
        try:
            result = subprocess.run(
                ["pytest"],
                capture_output=True,
                text=True,
                check=True
            )
            return RunResult(passed=True, output=result.stdout)
        except subprocess.CalledProcessError as e:
            return RunResult(passed=False, output=e.stdout + e.stderr)

class CopilotLogPolicy(Policy):
    def check(self, pr_data: dict) -> PolicyResult:
        if "## 🤖 Copilot Consultation Log" in pr_data.get("description", ""):
            return PolicyResult(passed=True, message="Copilot log found.")
        else:
            return PolicyResult(passed=False, message="Missing Copilot Consultation Log.")

# --- The Orchestrator ---
class ReviewAgent:
    def __init__(self, vcs_provider: VCSProvider, test_runner: TestRunner, policies: list[Policy]):
        self.vcs = vcs_provider
        self.runner = test_runner
        self.policies = policies

    def process_pr(self, pr_data: dict):
        pr_id = pr_data["id"]
        print(f"Processing PR #{pr_id}...")

        # 1. Run Policy Checks
        policy_errors = []
        for policy in self.policies:
            policy_result = policy.check(pr_data)
            if not policy_result.passed:
                policy_errors.append(policy_result.message)

        if policy_errors:
            message = f"❌ Checks failed. Please review the logs.\n\n**Policy Check:**\n" + "\n".join(policy_errors)
            self.vcs.post_comment(pr_id, message)
            return

        # 2. Run Tests
        test_result = self.runner.run()
        if not test_result.passed:
            message = f"❌ Checks failed. Please review the logs.\n\n**Test Results:**\n```\n{test_result.output}\n```"
            self.vcs.post_comment(pr_id, message)
            return # Stop processing

        # 3. Merge if all checks passed
        self.vcs.post_comment(pr_id, "✅ All checks passed. Merging PR.")
        self.vcs.merge_pr(pr_id)

    def process_open_prs(self):
        open_prs = self.vcs.get_open_prs()
        if not open_prs:
            print("No open PRs found.")
            return
        for pr_data in open_prs:
            self.process_pr(pr_data)

# --- Entry Point ---
if __name__ == "__main__":
    # This demonstrates how dependencies are injected
    agent = ReviewAgent(
        vcs_provider=GitHubProvider(),
        test_runner=PytestRunner(),
        policies=[CopilotLogPolicy()]
    )
    # In a real CI/CD environment, this would be triggered by a webhook
    # For now, we can run it manually.
    # agent.process_open_prs()