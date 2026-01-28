import sys
import os
from pydantic import BaseModel

# Import our custom modules
from product.curator import app as curator_app
from product.researcher import search_author_interview, get_transcript_text, get_hn_comments
from product.analyst_core import app as analyst_app
from product.broadcaster import generate_podcast_script, synthesize_audio

class PipelineOutput(BaseModel):
    summary: str
    confidence: float

def run_pipeline(topic: str) -> PipelineOutput | None:
    """
    Runs the full product pipeline for a given topic and returns structured output.
    """
    print(f"🔥 Starting learning system for topic: {topic}")
    print("="*60)
    
    # Phase 1: Curator
    print("\n[Step 1] Starting Curator Agent...")
    curator_result = curator_app.invoke({"topic": topic})
    selected_book = curator_result.get("selected_book")
    
    if not selected_book:
        print("❌ Book selection failed, terminating process.")
        return None

    print(f"✅ Book locked: 《{selected_book['title']}》")
    
    # Phase 2: Content Fetcher
    print("\n[Step 2] Aggregating multi-dimensional data (YouTube + Hacker News)...")
    video_id = search_author_interview(selected_book['title'], selected_book['authors'])
    youtube_text = get_transcript_text(video_id) if video_id else ""
    hn_comments = get_hn_comments(selected_book['title'])
    
    raw_text = f"""
    Book Title: {selected_book['title']}
    Description: {selected_book['description']}
    
    --- YouTube Interview Transcript ---
    {youtube_text or "No interview available."}
    
    --- Hacker News Engineer Discussions ---
    {hn_comments or "No discussions available."}
    """
    
    if not youtube_text and not hn_comments:
        print("⚠️ External data sources depleted. Activating Gemini's internal knowledge...")
        raw_text += "\n[System Instruction]: External data is missing. Please use your internal training knowledge about this book to perform the analysis."

    # Phase 3: Analyst
    print("\n[Step 3] Starting Analyst Agent (Gemini 2.5 Pro)...")
    print("Compiling business content into engineering architecture document...")
    
    analyst_result = analyst_app.invoke({
        "original_text": raw_text, 
        "revision_count": 0
    })
    
    # Phase 4: Broadcaster
    print(f"\n[Step 4] Starting Broadcaster Agent...")
    script = generate_podcast_script(analyst_result["draft_analysis"])
    synthesize_audio(script)
    
    # Create the final output object
    # Placeholder for confidence score, as it's not yet implemented.
    output = PipelineOutput(summary=analyst_result["draft_analysis"], confidence=0.95)

    return output


def run(topic: str):
    """
    Legacy run function for existing calls.
    Executes the pipeline and prints the summary.
    """
    result = run_pipeline(topic)
    if result:
        print("="*60)
        print("🚀 [Compilation Complete] Learning document for engineers:")
        print("="*60)
        print(result.summary)
        print("\n🎉 System execution complete! Open output_podcast.mp3 to listen to your learning outcome.")

def main():
    """Main entry point for command-line execution."""
    user_topic = "B2B Sales for Startups"
    if len(sys.argv) > 1:
        user_topic = sys.argv[1]
    run(user_topic)


if __name__ == "__main__":
    main()
