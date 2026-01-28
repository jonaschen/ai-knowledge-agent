import pytest
from unittest.mock import patch, MagicMock
from product import main

def test_main_exits_on_curator_failure():
    """
    Verify that the main script exits with a non-zero code if the Curator returns None.
    """
    # Arrange: Mock the Curator to simulate a failure (returning an empty dict)
    with patch('product.curator.app.invoke', return_value={}) as mock_invoke:

        # Act & Assert: Expect a SystemExit with a non-zero exit code
        with pytest.raises(SystemExit) as e:
            main.run_pipeline("non_existent_topic")

        # Assert that the exit code is 1 (or any non-zero value)
        assert e.type == SystemExit
        assert e.value.code == 1

        # Verify the mock was called
        mock_invoke.assert_called_once_with({"topic": "non_existent_topic"})

def test_main_exits_on_broadcaster_failure():
    """
    Verify that the main script exits with a non-zero code if the Broadcaster script generation fails.
    """
    # Arrange: Mock dependencies to allow the pipeline to reach the broadcaster
    mock_book = {
        'title': "Test Title",
        'authors': ["Test Author"],
        'description': "A test book."
    }
    mock_analyst_result = {"draft_analysis": "This is a test analysis."}

    with patch('product.curator.app.invoke', return_value={"selected_book": mock_book}), \
         patch('product.researcher.search_author_interview', return_value="video_id"), \
         patch('product.researcher.get_transcript_text', return_value="transcript"), \
         patch('product.researcher.get_hn_comments', return_value="comments"), \
         patch('product.analyst_core.app.invoke', return_value=mock_analyst_result), \
         patch('product.main.generate_podcast_script', return_value=[]) as mock_generate_script, \
         patch('product.main.synthesize_audio') as mock_synthesize_audio: # Simulate failure

        # Act & Assert: Expect a SystemExit
        with pytest.raises(SystemExit) as e:
            main.run_pipeline("test_topic")

        assert e.type == SystemExit
        assert e.value.code == 1

        # Verify the broadcaster script generation was called, but synthesis was not
        mock_generate_script.assert_called_once()
        mock_synthesize_audio.assert_not_called()

def test_main_exits_on_audio_synthesis_failure():
    """
    Verify that the main script exits with a non-zero code if audio synthesis fails.
    """
    # Arrange: Mock dependencies to allow the pipeline to reach audio synthesis
    mock_book = {
        'title': "Test Title",
        'authors': ["Test Author"],
        'description': "A test book."
    }
    mock_analyst_result = {"draft_analysis": "This is a test analysis."}
    mock_script = [{"speaker": "Alex", "text": "Hello"}]

    with patch('product.curator.app.invoke', return_value={"selected_book": mock_book}), \
         patch('product.researcher.search_author_interview', return_value="video_id"), \
         patch('product.researcher.get_transcript_text', return_value="transcript"), \
         patch('product.researcher.get_hn_comments', return_value="comments"), \
         patch('product.analyst_core.app.invoke', return_value=mock_analyst_result), \
         patch('product.main.generate_podcast_script', return_value=mock_script), \
         patch('product.main.synthesize_audio', return_value=None) as mock_synthesize_audio: # Simulate failure

        # Act & Assert: Expect a SystemExit
        with pytest.raises(SystemExit) as e:
            main.run_pipeline("test_topic")

        assert e.type == SystemExit
        assert e.value.code == 1

        # Verify that synthesize_audio was called
        mock_synthesize_audio.assert_called_once_with(mock_script)
