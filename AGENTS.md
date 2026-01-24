# AI Software Studio Constitution (v2.1)

## 1. Core Philosophy: Evidentialism & Automation

* **Objective:** Build a self-evolving "Deep Context Reader" system.
* **Principle 1: Evidentialism.** No hallucinations. All claims must be backed by Researcher findings.
* **Principle 2: Automation.** The `studio/` layer manages the `product/` layer.
* **Principle 3: TDD.** Red-Green-Refactor is mandatory for all code changes.

---

## 2. Official Directory Structure (The Territory)

All agents MUST respect this structure. **DO NOT** delete files listed here unless explicitly instructed.

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
│   └── pm.py               # [Product Owner] Requirement breakdown & Planning
│
├── tests/                  <-- [Quality Gate]
│   ├── test_curator.py
│   ├── test_researcher.py
│   ├── test_analyst.py
│   └── ...
└── AGENTS.md               # [The Constitution] Single Source of Truth

```

---

## 3. Agent Responsibilities

### Studio Agents (Internal Tools)

* **Architect:** Reads this file. Plans features. Enforces TDD.
* **ReviewAgent:** Monitors PRs. Runs `pytest`. Merges **ONLY** if green.
* **ProductManager (PM):** High-level planner. Generates execution plans JSON.

### Product Agents (The Application)

* **Curator:** Fetches books via Google Books. Falls back to Tavily on 429 errors.
* **Researcher:** Searches the web for "deep reviews" and "counter-arguments".
* **Analyst:** Synthesizes book content + researcher notes into a recursive thematic tree.
* **Broadcaster:** Converts the tree into a structured dialogue script.

---

## 4. Coding Standards

* **Imports:** Use absolute imports where possible (e.g., `from product.researcher import Researcher`).
* **Error Handling:** Never crash on API limits. Implement fallbacks (e.g., Google -> Tavily).
* **Testing:** All PRs must include a test file in `tests/`.

---

## 5. Knowledge Management & Continuous Learning (The Memory)

To prevent repetitive mistakes and "Agentic Loops", all agents must adhere to the following memory protocols:

### Review History is the Oracle
The file `studio/review_history.md` contains the log of past PR failures, error analyses, and architectural decisions.

* **Jules (Developer):** Before writing any code, you **MUST** read `studio/review_history.md`. Check if a similar task has failed before. If so, analyze the "Root Cause" and "Fix Suggestion" to avoid repeating the same mistake.
* **ReviewAgent:** You are the scribe. You must update this file with test results, specifically noting why a test failed (e.g., "Pydantic Mock Error").
* **Architect:** When planning a new feature or recovery, refer to this history to adjust the strategy.

### Failure is Knowledge
* If a PR is closed or code is reverted, the lesson learned must be preserved in `studio/review_history.md`.
* Never delete history from this file unless it is a refactor of the history itself.
