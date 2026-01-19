# AGENTS.md - Context & Directives for Google Jules

## Project Goal
Build an automated "High-Intensity Business Thinking Learning System" using LangGraph.
Target audience: Senior Engineers transitioning to Entrepreneurship.

## Architecture Stack
- **Orchestration**: LangGraph (StateGraph)
- **LLM**: Google Vertex AI (Gemini 2.5 Pro / Flash)
- **TTS**: Google Cloud TTS (Chirp 3)
- **Language**: Python 3.11+ (Type Hints required)

## Critical Constraints (The "Vibe")
1. **Isomorphic Mapping**: When analyzing business books, ALWAYS map concepts to Distributed Systems metaphors (e.g., Marketing -> Traffic Shaping).
2. **State Management**: Use `TypedDict` for graph state. Never assume global variables.
3. **Environment**: NEVER hardcode Project IDs (like "project-391688be..."). Always use `os.getenv`.
4. **Async**: All I/O (Network, API) must be asynchronous.

## Directory Structure
- `analyst_core.py`: The brain (LangGraph node logic).
- `broadcaster.py`: TTS and Script generation.
- `curator.py`: Book searching and HN filtering.
