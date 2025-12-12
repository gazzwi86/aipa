---
name: youtube-summarizer
description: Extract and summarize YouTube video transcripts
triggers:
  - youtube.com
  - youtu.be
  - summarize video
  - what's this video about
  - video summary
  - youtube
---

# YouTube Summarizer Skill

Extract transcripts from YouTube videos and provide comprehensive summaries.

## When to Activate

- YouTube URL shared in conversation
- "Summarize this video"
- "What's this YouTube video about?"
- "Give me the key points from this video"

## Capabilities

### Transcript Extraction
Extract the full transcript from YouTube videos (where available).

### Summary Generation
Create concise summaries with:
- Main topic/thesis
- Key points
- Notable quotes
- Timestamps for important moments

### Content Analysis
Analyze content for:
- Claims and assertions
- Educational value
- Speaker expertise
- Bias indicators

## Dependencies

Requires `youtube-transcript-api` package:
```toml
# pyproject.toml
dependencies = [
    "youtube-transcript-api>=0.6.0",
]
```

## Implementation

### Extract Video ID

```python
import re

def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
```

### Get Transcript

```python
from youtube_transcript_api import YouTubeTranscriptApi

def get_transcript(video_id: str) -> list[dict] | None:
    """Get transcript for a YouTube video."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception:
        return None

def format_transcript(transcript: list[dict]) -> str:
    """Format transcript into readable text."""
    return " ".join(entry["text"] for entry in transcript)
```

## Summary Template (Fabric-style)

### Brief Summary
> This video is about [topic]. The main points are:
> 1. [Point 1]
> 2. [Point 2]
> 3. [Point 3]

### Detailed Summary
```markdown
## Video Summary

**Title**: [Video Title]
**Channel**: [Channel Name]
**Duration**: [Length]
**URL**: [URL]

### Overview
[1-2 paragraph summary of the video's content and purpose]

### Key Points
1. **[Point 1]** (timestamp)
   - Supporting detail
2. **[Point 2]** (timestamp)
   - Supporting detail
3. **[Point 3]** (timestamp)
   - Supporting detail

### Notable Quotes
> "[Quote 1]" - timestamp
> "[Quote 2]" - timestamp

### Takeaways
- [Actionable takeaway 1]
- [Actionable takeaway 2]

### Critical Notes
- [Any bias or limitations noted]
- [Fact-check recommendations]
```

## Response Format

### Voice (Brief)
> "This is a 15-minute video about productivity systems. The main points are: first, time blocking is more effective than to-do lists; second, energy management matters more than time management; and third, regular reviews are essential. Want me to go deeper on any of these?"

### Text (Detailed)
Full markdown summary with timestamps, quotes, and analysis.

## Error Handling

### No Transcript Available
> "This video doesn't have a transcript available. This usually means captions haven't been enabled by the creator. I can't summarize it without the transcript."

### Private/Deleted Video
> "I can't access this video. It might be private, deleted, or age-restricted."

### Invalid URL
> "That doesn't look like a valid YouTube URL. Please share a link in the format youtube.com/watch?v=... or youtu.be/..."

## MCP Servers

- None required (uses Python package directly)
- Optional: `playwright` for video metadata if needed

## Quality Guidelines

1. **Accuracy**: Stick to what's actually said in the video
2. **Attribution**: Note when something is the speaker's opinion vs fact
3. **Timestamps**: Include timestamps for key moments
4. **Brevity**: Match summary length to video length
5. **Objectivity**: Don't inject personal opinions
