---
name: content-summarizer
description: Summarize articles, videos, documents, and local files
triggers:
  - summarize
  - summary
  - tldr
  - youtube.com
  - youtu.be
  - what's this about
  - summarize video
  - video summary
  - summarize the file
  - analyze the document
  - what's in this file
---

# Content Summarizer Skill

Summarize various content types including web articles, YouTube videos, and local files.

## When to Activate

- "Summarize this article"
- "What's this video about?"
- "TLDR of..."
- YouTube URL shared
- Long article URL shared
- "Summarize the file I uploaded"
- "What's in test.pdf?"
- "Analyze this document"

## Supported Content

| Type | How | Triggers |
|------|-----|----------|
| Web articles | Fetch via Playwright and summarize | URL shared |
| YouTube videos | Extract transcript via API | youtube.com, youtu.be |
| Local files (PDF) | Read with pypdf/pdfplumber | "summarize file", "analyze document" |
| Local files (TXT/MD) | Read directly | File path mentioned |
| Long text | Condense inline | "TLDR", "summarize this" |

## Summary Structure

### Voice (Brief)
> "This is about X. The main points are Y and Z."

### Text (Detailed)
```markdown
## Summary
One paragraph overview.

## Key Points
1. First main point
2. Second main point
3. Third main point

## Notable Details
- Interesting detail
- Important caveat

## Source
[Title](url) or File: filename
```

---

## YouTube Video Handling

### Dependencies

Requires `youtube-transcript-api` package (already in pyproject.toml).

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

### YouTube Summary Template

```markdown
## Video Summary

**Title**: [Video Title]
**Channel**: [Channel Name]
**Duration**: [Length]
**URL**: [URL]

### Overview
[1-2 paragraph summary]

### Key Points
1. **[Point 1]** (timestamp)
2. **[Point 2]** (timestamp)
3. **[Point 3]** (timestamp)

### Notable Quotes
> "[Quote]" - timestamp

### Takeaways
- [Actionable takeaway]
```

### YouTube Error Handling

- **No transcript**: "This video doesn't have a transcript available."
- **Private/deleted**: "I can't access this video."
- **Invalid URL**: "That doesn't look like a valid YouTube URL."

---

## Local File Handling

### Supported File Types

| Extension | Method | Notes |
|-----------|--------|-------|
| `.txt` | Direct read | Plain text |
| `.md` | Direct read | Markdown |
| `.pdf` | pypdf/pdfplumber | Extract text from PDF |
| `.py`, `.js`, etc. | Direct read | Code files |

### Finding Files

Files are typically located in the workspace:
- User uploads: `/workspace/files/`
- Current directory files

### PDF Reading

```python
from pypdf import PdfReader

def read_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text
```

### Local File Summary Template

```markdown
## Document Summary

**File**: [filename]
**Type**: [PDF/Text/Markdown]
**Size**: [pages/words]

### Overview
[Summary of document content]

### Key Points
1. [Main point]
2. [Supporting point]
3. [Conclusion/finding]

### Notable Sections
- [Important section]: [Brief description]

### Metadata
- Created/Modified: [if available]
- Author: [if available]
```

### File Error Handling

- **File not found**: "I couldn't find a file named 'X'. Check the path or upload the file first."
- **Can't read PDF**: "I couldn't extract text from this PDF. It might be scanned or encrypted."
- **Unsupported format**: "I can't read [format] files. Try PDF, TXT, or MD."

---

## Summary Guidelines

- Lead with the main point
- Capture key arguments/findings
- Note any conclusions
- Mention author/source credibility
- Keep it proportional (longer content = slightly longer summary)

## Quality Checks

- Don't editorialize (stick to what's said)
- Preserve nuance
- Note if content is opinion vs fact
- Mention publication date if relevant
- For YouTube: include timestamps for key moments
- For files: note document structure if relevant

## MCP Servers

- `playwright` - Fetch web content
- `notion` - Save summaries if requested

## Save to Notion

When substantial summary completed:
1. Ask: "Should I save this summary to your Notes?"
2. If yes, create Note with category based on content type
3. Include source URL or file path
