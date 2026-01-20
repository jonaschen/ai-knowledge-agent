# AGENTS.md - Deep Context Reader

## Project Goal
Create a high-quality "Deep Dive" podcast about technical and business books.
Focus on ACCURACY, CONTEXT, and EXTERNAL VALIDATION.

## The Core Vibe
1. **No Hallucinations**: Never invent content. If it's not in the source text or search results, don't say it.
2. **Context is King**: Always discuss the book *in context*. What do critics say? What is the controversy?
3. **Structured Deep Dive**:
   - Intro: Why this book matters now.
   - Core Idea 1 + External evidence/opinion.
   - Core Idea 2 + External evidence/opinion.
   - Conclusion: Who should read this?

## Agent Roles
- **Curator**: Fetches the book AND specifically searches for "high quality reviews" and "Hacker News discussions". Packs them into `context_bundle`.
- **Analyst**: Synthesizes the book summary with the external reviews. Creates a script that explicitly cites sources (e.g., "Reviewers on Hacker News noted that...").
- **Broadcaster**: Renders the script into professional audio. Uses clear, paced delivery (SSML).
