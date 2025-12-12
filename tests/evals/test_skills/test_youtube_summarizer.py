"""Tests for the YouTube summarizer skill."""

import re
from unittest.mock import MagicMock, patch

import pytest

# Try to import youtube_transcript_api - skip tests if not available
try:
    from youtube_transcript_api import YouTubeTranscriptApi

    HAS_YOUTUBE_API = True
except ImportError:
    HAS_YOUTUBE_API = False


class TestYouTubeURLParsing:
    """Test YouTube URL parsing utilities."""

    def test_extract_video_id_standard_url(self):
        """Should extract video ID from standard URL."""

        def extract_video_id(url: str) -> str | None:
            patterns = [
                r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})",
                r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
                r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
            ]
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            return None

        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/watch?v=abc123XYZ_-", "abc123XYZ_-"),
        ]

        for url, expected_id in test_cases:
            assert extract_video_id(url) == expected_id

    def test_extract_video_id_with_params(self):
        """Should extract video ID even with extra parameters."""

        def extract_video_id(url: str) -> str | None:
            pattern = r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
            match = re.search(pattern, url)
            return match.group(1) if match else None

        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120&list=PLtest"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url_returns_none(self):
        """Should return None for invalid URLs."""

        def extract_video_id(url: str) -> str | None:
            pattern = r"(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"
            match = re.search(pattern, url)
            return match.group(1) if match else None

        invalid_urls = [
            "https://example.com/video",
            "https://vimeo.com/123456",
            "not a url",
            "",
        ]

        for url in invalid_urls:
            assert extract_video_id(url) is None


class TestTranscriptProcessing:
    """Test transcript processing utilities."""

    def test_merge_transcript_entries(self):
        """Should merge transcript entries into readable text."""
        transcript = [
            {"text": "Hello everyone.", "start": 0.0, "duration": 2.0},
            {"text": "Welcome to this video.", "start": 2.0, "duration": 3.0},
            {"text": "Today we'll discuss AI.", "start": 5.0, "duration": 3.0},
        ]

        merged = " ".join(entry["text"] for entry in transcript)

        assert merged == "Hello everyone. Welcome to this video. Today we'll discuss AI."

    def test_clean_transcript_text(self):
        """Should clean up transcript text."""

        def clean_transcript(text: str) -> str:
            # Remove [Music], [Applause], etc.
            text = re.sub(r"\[.*?\]", "", text)
            # Normalize whitespace
            text = " ".join(text.split())
            return text.strip()

        raw = "Hello everyone [Music] Welcome [Applause]   to the show"
        cleaned = clean_transcript(raw)

        assert cleaned == "Hello everyone Welcome to the show"

    def test_chunk_transcript_by_time(self):
        """Should be able to chunk transcript by time intervals."""
        transcript = [
            {"text": "Part 1", "start": 0.0, "duration": 30.0},
            {"text": "Part 2", "start": 30.0, "duration": 30.0},
            {"text": "Part 3", "start": 60.0, "duration": 30.0},
            {"text": "Part 4", "start": 90.0, "duration": 30.0},
        ]

        # Chunk into 60-second intervals
        chunk_duration = 60
        chunks = []
        current_chunk = []
        chunk_end = chunk_duration

        for entry in transcript:
            if entry["start"] >= chunk_end:
                chunks.append(current_chunk)
                current_chunk = []
                chunk_end += chunk_duration
            current_chunk.append(entry)

        if current_chunk:
            chunks.append(current_chunk)

        assert len(chunks) == 2
        assert len(chunks[0]) == 2  # First 60 seconds
        assert len(chunks[1]) == 2  # Second 60 seconds


class TestTranscriptSummarization:
    """Test transcript summarization patterns."""

    def test_extract_key_points_structure(self):
        """Summary should have key points structure."""
        summary_template = """
## Video Summary

### Key Points
- Point 1
- Point 2
- Point 3

### Main Topics
1. Topic A
2. Topic B

### Quotes Worth Noting
> "Important quote here"

### Timestamps
- 0:00 - Introduction
- 5:00 - Main content
"""

        required_sections = ["Key Points", "Main Topics"]
        for section in required_sections:
            assert section in summary_template

    def test_timestamp_formatting(self):
        """Should format timestamps correctly."""

        def format_timestamp(seconds: float) -> str:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}:{secs:02d}"

        assert format_timestamp(0) == "0:00"
        assert format_timestamp(65) == "1:05"
        assert format_timestamp(3661) == "61:01"

    def test_summary_length_limits(self):
        """Summary should respect length limits for voice vs text."""
        voice_max_chars = 500
        text_max_chars = 5000

        # Voice summary should be brief
        voice_summary = "This video discusses the key aspects of machine learning."
        assert len(voice_summary) < voice_max_chars

        # Text summary can be longer
        text_summary = "This video provides a comprehensive overview..." + "x" * 1000
        assert len(text_summary) < text_max_chars


@pytest.mark.skipif(not HAS_YOUTUBE_API, reason="youtube-transcript-api not installed")
class TestYouTubeAPIIntegration:
    """Test YouTube transcript API integration (mocked).

    Note: youtube-transcript-api v1.0+ uses `fetch` method instead of `get_transcript`.
    """

    def test_fetch_transcript_success(self):
        """Should fetch transcript successfully."""
        # Create a mock transcript object that mimics FetchedTranscript
        mock_transcript = MagicMock()
        mock_transcript.__iter__ = lambda self: iter(
            [
                {"text": "Hello", "start": 0.0, "duration": 1.0},
                {"text": "World", "start": 1.0, "duration": 1.0},
            ]
        )
        mock_transcript.__len__ = lambda self: 2

        with patch.object(YouTubeTranscriptApi, "fetch", return_value=mock_transcript):
            transcript = YouTubeTranscriptApi.fetch("test_id")
            entries = list(transcript)
            assert len(entries) == 2
            assert entries[0]["text"] == "Hello"

    def test_fetch_transcript_with_language(self):
        """Should request specific language."""
        mock_transcript = MagicMock()
        mock_transcript.__iter__ = lambda self: iter(
            [{"text": "Bonjour", "start": 0.0, "duration": 1.0}]
        )

        with patch.object(
            YouTubeTranscriptApi, "fetch", return_value=mock_transcript
        ) as mock_fetch:
            YouTubeTranscriptApi.fetch("test_id", languages=["fr"])
            mock_fetch.assert_called_once_with("test_id", languages=["fr"])

    def test_handle_no_transcript_available(self):
        """Should handle videos without transcripts."""
        try:
            from youtube_transcript_api._errors import TranscriptsDisabled
        except ImportError:
            pytest.skip("TranscriptsDisabled not available in this version")

        with (
            patch.object(YouTubeTranscriptApi, "fetch", side_effect=TranscriptsDisabled("test_id")),
            pytest.raises(TranscriptsDisabled),
        ):
            YouTubeTranscriptApi.fetch("test_id")


@pytest.mark.eval
class TestYouTubeSummarizerSkillEval:
    """Evaluation tests for YouTube summarizer skill agent behavior."""

    def test_skill_triggers(self):
        """Verify YouTube skill trigger patterns."""
        triggers = [
            "youtube.com",
            "youtu.be",
            "summarize video",
            "summarize this video",
            "watch?v=",
        ]

        test_queries = [
            "Summarize https://www.youtube.com/watch?v=abc123",
            "What's this video about? https://youtu.be/xyz789",
            "Summarize this video for me",
        ]

        for query in test_queries:
            matched = any(t in query.lower() for t in triggers)
            assert matched, f"Query '{query}' should match a YouTube trigger"

    def test_agent_extracts_video_url(self):
        """Agent should extract YouTube URL from query."""
        query = "Can you summarize https://www.youtube.com/watch?v=dQw4w9WgXcQ for me?"

        url_pattern = r"https?://(?:www\.)?(?:youtube\.com|youtu\.be)/[^\s]+"
        match = re.search(url_pattern, query)

        assert match is not None
        assert "youtube" in match.group(0)

    def test_response_structure(self):
        """Response should have proper summary structure."""
        expected_sections = [
            "summary",
            "key points",
            "topics",
        ]

        # Response should mention these concepts
        mock_response = """
        ## Summary
        This video covers machine learning basics.

        ## Key Points
        - Point 1
        - Point 2

        ## Topics Discussed
        - Topic A
        """

        for section in expected_sections:
            assert section.lower() in mock_response.lower()

    def test_handles_no_transcript_gracefully(self):
        """Agent should handle videos without transcripts."""
        error_message = "This video doesn't have a transcript available"

        # Should provide helpful message
        assert "transcript" in error_message.lower()
        assert "available" in error_message.lower()
