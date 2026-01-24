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


