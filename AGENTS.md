# AI Software Studio Constitution (v2.3)

## 1. Core Philosophy: Evidentialism & Automation

**Objective:** Build a self-evolving "Deep Context Reader" system.

**Principle 1:** Evidentialism. No hallucinations. All claims must be backed by Researcher findings.

**Principle 2:** Automation. The studio/ layer manages the product/ layer.

**Principle 3:** TDD. Red-Green-Refactor is mandatory for all code changes.

**Principle 4:** Refactor according to the SOLID principles.
 

---

## 2. Official Directory Structure (The Territory)

All agents MUST respect this structure. DO NOT delete files listed here unless explicitly instructed.

```text
/
├── product/                <-- [Production Line] The core content generation system
│   ├── main.py             # Entry point & Orchestrator
│   ├── curator.py          # Book Selection & Reliability Filter (Fallback: Tavily)
│   ├── researcher.py       # [The Eyes] Web Search & Evidence Gathering (Tavily API)
│   ├── analyst_core.py     # [The Brain] Deep Thematic Analysis (Recursive Tree)
│   └── broadcaster.py      # [The Voice] TTS Generation (Chirp 3)
│
├── studio/                 <-- [Management Layer] Tools that build the product
│   ├── architect.py        # [Tech Lead] Translates goals into TDD Issues
│   ├── review_agent.py     # [QA/Ops] Automated PR testing & merging
│   ├── pm.py               # [Product Owner] Requirement breakdown & Planning
│   ├── review_history.md   # [Active Memory] Recent failures & lessons (Max 500 lines)
│   └── rules.md            # [Long-term Memory] Design Patterns & Best Practices
│
├── tests/                  <-- [Quality Gate]
│   ├── test_curator.py
│   ├── test_researcher.py
│   ├── test_analyst.py
│   └── ...
└── AGENTS.md               # [The Constitution] Single Source of Truth
```

## 3. Agent Responsibilities

### Studio Agents (Internal Tools)

* **Architect:** Reads this file. Plans features. Enforces TDD.

* **ReviewAgent:** Monitors and review PRs. Runs pytest. Merges ONLY if green.

* **ProductManager (PM):** High-level planner. Generates execution plans JSON.
* * The Product Manager (PM) Agent is the **owner of product intent and product quality**.
  * The PM Agent does not produce content or code.
  * Its responsibility is to define **what meaningful output is** and to judge **whether the Product Team’s output delivers real user value**.

### Product Agents (The Application)

* **Curator:** Fetches books via Google Books. Falls back to Tavily on 429 errors.

* **Researcher:** Searches the web for "deep reviews" and "counter-arguments".

* **Analyst:** Synthesizes book content + researcher notes into a recursive thematic tree.

* **Broadcaster:** Converts the tree into a structured dialogue script.

## 4. Coding Standards

* **Imports:** Use absolute imports where possible (e.g., from product.researcher import Researcher).

* **Error Handling:** Never crash on API limits. Implement fallbacks (e.g., Google -> Tavily).

* **Testing:** All PRs must include a test file in tests/.

## 5. Knowledge Management & Continuous Learning (The Memory)

To prevent repetitive mistakes and "Agentic Loops", all agents must adhere to the following memory protocols:

### Structured Logging (Mandatory)

All entries in studio/review_history.md MUST follow this format to ensure machine readability:

```text
## [PR #<ID>] <Component> Failure
- **Date**: YYYY-MM-DD
- **Error Type**: <e.g., PydanticValidationError, APITimeout>
- **Root Cause**: <Brief description>
- **Fix Pattern**: <Actionable instruction for future>
- **Tags**: #mocking, #pydantic, #api
```

### Context Window Management (Archival Protocol)

**Trigger:** When studio/review_history.md exceeds 500 lines.

**Action (Architect):**

* **Summarize:** Extract universal "Fix Patterns" and add them to studio/rules.md.

* **Archive:** Move the detailed logs to studio/archive/review_history_YYYY_MM.md.

* **Reset:** Clear studio/review_history.md to keep it lightweight.


### Failure is Knowledge

If a PR is closed or code is reverted, the lesson learned must be preserved in review_history.md.

Jules (Developer): Before writing any code, you MUST read studio/rules.md (for best practices) and studio/review_history.md (for recent pitfalls).

---

## 6. The Copilot Protocol (Model Diversity & Enforcement)

**Core Principle:** Use heterogeneous models (Gemini + Copilot) to reduce hallucinations. This process is NON-NEGOTIABLE.

**Workflow:** The "Double Check" Mechanism

* **Develop (Gemini):** Jules writes the code and ensures tests pass (Green state).

* **Consult (Copilot):** Before committing, Jules MUST invoke the GitHub Copilot CLI.

* **Command:** gh copilot suggest "Review this code for optimization and security: [paste code snippet]"

* **Action:** Analyze Copilot's response.

* * **If valid improvement:** Apply it (Refactor).

* * **If hallucination/breakage:** Reject it.

**Documentation (The Audit Trail):** Jules MUST append a COCKPIT_CONSULTATION_LOG.md file (or section in PR description) with the consultation details.


### Circuit Breaker (Anti-Loop Protocol)

To prevent infinite loops where Copilot suggestions break the build:

* **3-Strike Limit:** If Copilot's suggestions cause tests to fail, you may attempt to fix it TWICE.

* **Abort Condition:** On the 3rd failure, you MUST ABORT the refactoring process.

* **Fallback Action:** Revert the code to the state at the end of Phase 2 (Green). Do not sacrifice correctness for optimization.

* **Logging:** Explicitly state "Aborted due to Circuit Breaker" in the log.

### Documentation Format

Every Pull Request MUST include the following section. If missing, ReviewAgent will reject the PR.

```text
## 🤖 Copilot Consultation Log
- **Target Function**: `<name of function refactored>`
- **Copilot Advice**: `<Summary, e.g., 'Suggested using itertools'>`
- **Result**: `<Applied | Rejected | Aborted due to Circuit Breaker>`
```
