# AI Studio Design Patterns & Best Practices

This file serves as the **Long-term Memory** for the development team.
It contains universal patterns derived from past failures recorded in `review_history.md`.

> **Rule of Thumb:** Before implementing complex logic, check if a pattern here applies.

---

## 1. Testing Patterns (TDD)

### 1.1 Pydantic Model Mocking (The "Agentic Loop" Preventer)
* **Context:** LangChain uses Pydantic v2 heavily for data structures (e.g., `Generation`, `AIMessage`).
* **Problem:** Passing `MagicMock` objects to Pydantic fields (e.g., `Generation(text=mock_obj)`) causes `pydantic_core.ValidationError` because strict type checking rejects the Mock object.
* **Consequence:** This often leads to infinite **Agentic Loops** where the AI tries to fix the logic but fails to fix the test setup.
* **Solution:** Always use **concrete types (literals)** for Pydantic fields in tests. Do NOT mock the data container itself if it validates types.

**Code Example:**
```python
# ❌ BAD (Will fail validation)
mock_content = MagicMock()
result = Generation(text=mock_content) 

# ✅ GOOD (Passes validation)
result = Generation(text="actual string content")
```


### 1.2 External API Mocking

* **Rule:** Never let unit tests hit real APIs (Google Books, Tavily).
* **Pattern:** Use `unittest.mock.patch` for all network calls.
* **Safety Net:** Tests requiring real network access must be marked with `@pytest.mark.integration`.

---

## 2. Architecture Patterns

### 2.1 The "Fallback" Pattern

* **Context:** Critical dependencies (like Google Books API) have rate limits.
* **Rule:** Primary data sources MUST have a secondary fallback implemented within the same node or function.
* **Example:** ```python
try:
return GoogleBooks.search(query)
except RateLimitError:
return Tavily.search(query)


---

## 3. Coding Standards

* **Environment Variables:** Always load via `dotenv.load_dotenv()` at the entry point (if `__name__ == "__main__":`).
* **Type Hinting:** Use Python 3.10+ type hints (`list[str] | None`) for clarity.


---

