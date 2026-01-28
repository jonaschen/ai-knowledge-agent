# AI Software Studio Constitution (v3.1)

> **Purpose**  
> This document defines the constitutional laws governing the AI Software Studio.  
> Its goal is to enable *safe, reliable, and auditable self-evolution* of an AI-driven software factory.

---

## 1. Core Philosophy: Self-Evolution & SOLID

### Objective
Build a **Self-Evolving Cognitive Software Factory** that improves its own intelligence, quality, and reliability over time **with minimal human intervention**, while remaining structurally stable.

### Foundation
All agents, prompts, and orchestration logic **MUST adhere to SOLID principles** to ensure the system remains robust during self-evolution.

Self-evolution is **constrained evolution**, not uncontrolled mutation.

---

## 2. The SOLID Mandate for AI Agents

### SRP — Single Responsibility Principle
Each Agent MUST have **one and only one reason to change**.

**Examples**
- Curator selects books. It MUST NOT summarize them.
- Researcher fetches data. It MUST NOT analyze sentiment.
- Analyst synthesizes. It MUST NOT browse or fetch raw sources.

An agent that violates SRP is considered **architecturally invalid**.

---

### OCP — Open/Closed Principle
Agents MUST be:
- **Open for extension**
- **Closed for modification**

#### Approved Extension Mechanism
- The primary extension point is the top-level `SYSTEM_PROMPT` or `PROMPT_TEMPLATE` variable.
- Prompt evolution is performed **only** via the Optimizer agent.

Core execution flow, I/O schema, and role definition MUST NOT be modified during prompt optimization.

---

### LSP — Liskov Substitution Principle
Derived agents, refactors, or model upgrades MUST remain substitutable.

**Example**
- Switching from `Gemini-1.5-Pro` to `Gemini-2.5-Pro` MUST NOT require:
  - Input schema changes
  - Output schema changes
  - Orchestrator logic changes

Breaking substitution is a **constitutional violation**.

---

### ISP — Interface Segregation Principle
Agents MUST NOT depend on tools, APIs, or capabilities they do not directly use.

**Examples**
- Analyst MUST NOT access search APIs directly.
- Researcher MUST NOT access synthesis or scoring logic.
- Agents receive data only via **Context Bundles**, not raw tool handles.

---

### DIP — Dependency Inversion Principle
High-level strategies MUST NOT depend on low-level implementations.

Both MUST depend on **explicit abstractions**, such as:
- JSON Schemas
- Typed Context Contracts
- Structured Output Definitions

Model providers, APIs, and tools are **replaceable details**, never foundations.

---

## 3. Directory Structure (The Territory)

```text
/
├── product/ # [Production Layer] The Factory Floor
│ ├── main.py # Entry point & Orchestrator (DIP-compliant)
│ ├── curator.py # SRP: Selection & Reliability
│ ├── researcher.py # SRP: Evidence Gathering (The Eyes)
│ ├── analyst_core.py # SRP: Synthesis (The Brain)
│ └── broadcaster.py # SRP: Audio Generation (The Voice)
│
├── studio/ # [Management Layer] The Brain Trust
│ ├── manager.py # [Autopilot] Health checks & routing
│ ├── optimizer.py # [Evolver] OPRO / Meta-Prompting
│ ├── architect.py # [Builder] Logic changes & TDD enforcer
│ ├── review_agent.py # [Guardian] QA, validation, log analysis
│ ├── pm.py # [Planner] Product intent & prioritization
│ ├── review_history.md # [Memory] Failure & regression logs
│ └── rules.md # [Wisdom] Design patterns & quality criteria
│
├── tests/ # [Quality Gate] TDD Assets
└── AGENTS.md # [Constitution] Single Source of Truth
```

---



---

## 4. Self-Evolution Protocols (OPRO)

Self-evolution is governed by a **strict, auditable optimization loop**.

### 4.1 Prompt Isolation (Hard Rule)
- Every agent script MUST define its system prompt as a **top-level variable**:
  - `SYSTEM_PROMPT` or `PROMPT_TEMPLATE`
- Prompts MUST NOT be embedded inside function calls or closures.

Violation of this rule breaks OCP and disables automated optimization.

---

### 4.2 Approved Evolution Surface

By default, **only the following surfaces are writable by the Optimizer**:

- `SYSTEM_PROMPT` / `PROMPT_TEMPLATE`

The following surfaces MAY exist but are **read-only unless explicitly unlocked**:

- Input / Output Schemas
- Scoring Rubrics
- Context Assembly Rules

This preserves safety while acknowledging future evolution needs.

---

### 4.3 The Optimization Loop

**Trigger**
- Manager detects:
  - High failure rate in `review_history.md`, OR
  - Low quality score in `main.py` output

**Action**
- Manager summons Optimizer

**Optimization**
- Optimizer reads:
  - Agent source code
  - Prompt definition
  - Failure logs
- Optimizer generates an improved prompt variant

**Verification**
- ReviewAgent runs:
  - TDD suite
  - Quality evaluation (as defined in `rules.md`)

**Deployment**
- Only if verification is GREEN:
  - Prompt is committed
  - Failure history is updated

---

## 5. Quality & Failure Semantics

All quality evaluations MUST be:

- **Explicit** (criteria are documented)
- **Logged** (stored in `review_history.md`)
- **Replayable** (same input yields comparable judgment)

Quality metrics are defined in `studio/rules.md` and treated as **first-class artifacts**.

---

## 6. Operational Roles

### Manager — *The Autopilot*
- Continuously monitors system health
- Routes work to:
  - Architect (logic defects)
  - Optimizer (quality degradation)

---

### Optimizer — *The Evolver*
- The ONLY agent authorized to modify:
  - `SYSTEM_PROMPT` variables
- Must NOT modify logic, schemas, or tests

---

### Architect — *The Builder*
- Implements new features and logic changes
- MUST follow strict TDD
- MUST NOT tune prompts

---

### Reviewer — *The Guardian*
- Enforces constitutional compliance
- Rejects any change that:
  - Breaks tests
  - Violates SOLID
  - Violates Copilot or evolution protocols

---

## 7. The Copilot Protocol (Transitional)

> **Status:** Transitional Human-Augmented Protocol

- During refactor phases, Jules MUST consult GitHub Copilot before committing.
- Anti-loop safeguard:
  - If Copilot-generated changes break tests **three times**, the changes MUST be reverted.

This protocol exists to stabilize the system during human–AI co-development and may be deprecated in future versions.

---

## 8. Final Principle

> **The system may evolve itself,  
> but it must always be able to explain, test, and reverse that evolution.**

Anything less is not self-improvement — it is entropy.
