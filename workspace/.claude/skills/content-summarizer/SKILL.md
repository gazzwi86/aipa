---
name: content-summarizer
description: Summarize articles, videos, and documents
triggers:
  - summarize
  - summary
  - tldr
  - youtube.com
  - what's this about
---

# Content Summarizer Skill

Summarize various content types.

## When to Activate

- "Summarize this article"
- "What's this video about?"
- "TLDR of..."
- YouTube URL shared
- Long article URL shared

## Supported Content

| Type | How |
|------|-----|
| Web articles | Fetch and summarize |
| YouTube videos | Transcript summary |
| Documents | Read and summarize |
| Long text | Condense |

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
[Title](url)
```

## Summary Guidelines

- Lead with the main point
- Capture key arguments/findings
- Note any conclusions
- Mention author/source credibility
- Keep it proportional (longer content = slightly longer summary)

## YouTube Handling

1. Extract video ID from URL
2. Get transcript (if available)
3. Summarize transcript
4. Note video length and channel

## MCP Servers

- `playwright` - Fetch web content
- `notion` - Save summaries if requested

## Quality Checks

- Don't editorialize (stick to what's said)
- Preserve nuance
- Note if content is opinion vs fact
- Mention publication date if relevant
