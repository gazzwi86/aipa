---
name: generate-pptx
description: Create PowerPoint presentations programmatically
triggers:
  - create presentation
  - make slides
  - generate pptx
  - powerpoint
  - slide deck
  - create deck
---

# PowerPoint Generation Skill

Create professional PowerPoint presentations programmatically using python-pptx.

## When to Activate

- "Create a presentation about..."
- "Make me a slide deck for..."
- "Generate a PowerPoint on..."
- "Create 10 slides about..."

## Capabilities

### Slide Types
- Title slides
- Content slides (text + bullets)
- Two-column layouts
- Image slides
- Chart slides
- Quote slides
- Section headers

### Styling
- Custom color themes
- Font selection
- Background colors
- Logo placement
- Consistent branding

### Content Generation
- Auto-generate content from outline
- Research topic and create slides
- Convert documents to presentations
- Summarize content into bullet points

## Implementation

### Basic Presentation

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RgbColor
from pptx.enum.text import PP_ALIGN

def create_presentation(title: str, slides_content: list[dict]) -> str:
    """Create a PowerPoint presentation.

    Args:
        title: Presentation title
        slides_content: List of slide dictionaries

    Returns:
        Path to generated .pptx file
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)  # 16:9
    prs.slide_height = Inches(7.5)

    # Title slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    slide.shapes.title.text = title

    # Content slides
    for content in slides_content:
        add_content_slide(prs, content)

    # Save
    filename = f"workspace/files/{title.lower().replace(' ', '_')}.pptx"
    prs.save(filename)
    return filename
```

### Slide Content Format

```python
slides_content = [
    {
        "type": "title",
        "title": "Introduction",
        "subtitle": "Getting Started with AI"
    },
    {
        "type": "bullets",
        "title": "Key Points",
        "bullets": [
            "First important point",
            "Second important point",
            "Third important point"
        ]
    },
    {
        "type": "two_column",
        "title": "Comparison",
        "left": ["Option A", "Feature 1", "Feature 2"],
        "right": ["Option B", "Feature 1", "Feature 2"]
    },
    {
        "type": "image",
        "title": "Architecture",
        "image_path": "workspace/files/diagram.png",
        "caption": "System Architecture"
    },
    {
        "type": "quote",
        "quote": "The best way to predict the future is to create it.",
        "attribution": "- Peter Drucker"
    }
]
```

### Add Content Slide

```python
def add_content_slide(prs, content: dict):
    """Add a content slide based on type."""
    slide_type = content.get("type", "bullets")

    if slide_type == "bullets":
        layout = prs.slide_layouts[1]  # Title and Content
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = content["title"]

        body = slide.shapes.placeholders[1]
        tf = body.text_frame

        for i, bullet in enumerate(content["bullets"]):
            if i == 0:
                tf.paragraphs[0].text = bullet
            else:
                p = tf.add_paragraph()
                p.text = bullet
                p.level = 0

    elif slide_type == "two_column":
        layout = prs.slide_layouts[3]  # Two Content
        slide = prs.slides.add_slide(layout)
        slide.shapes.title.text = content["title"]
        # Add left/right content...

    elif slide_type == "image":
        layout = prs.slide_layouts[6]  # Blank
        slide = prs.slides.add_slide(layout)
        # Add title and image...
```

### Styling Utilities

```python
def apply_theme(prs, theme: str = "professional"):
    """Apply a color theme to the presentation."""
    themes = {
        "professional": {
            "primary": RgbColor(0x00, 0x52, 0x8A),    # Dark blue
            "secondary": RgbColor(0x00, 0x96, 0xC7),  # Light blue
            "accent": RgbColor(0xFF, 0x6B, 0x35),     # Orange
            "text": RgbColor(0x33, 0x33, 0x33),       # Dark gray
        },
        "modern": {
            "primary": RgbColor(0x1A, 0x1A, 0x2E),    # Dark purple
            "secondary": RgbColor(0x16, 0x21, 0x3E),  # Navy
            "accent": RgbColor(0xE9, 0x4560),         # Pink
            "text": RgbColor(0xEE, 0xEE, 0xEE),       # Light gray
        }
    }
    return themes.get(theme, themes["professional"])
```

## Workflow

### From Topic

1. User: "Create a presentation about machine learning basics"
2. Research topic (if needed)
3. Generate outline
4. Create slides for each section
5. Save and return file path

### From Outline

1. User provides outline or bullet points
2. Convert to slides_content format
3. Generate presentation
4. Return file path

### From Document

1. User provides document/text
2. Extract key points
3. Organize into sections
4. Generate slides
5. Return file path

## Response Format

### Voice (Brief)
> "I've created a 12-slide presentation about machine learning basics. The file is saved to your workspace. Would you like me to add any specific sections or adjust the styling?"

### Text (Detailed)
```markdown
## Presentation Created

**File**: `workspace/files/machine_learning_basics.pptx`
**Slides**: 12

### Outline
1. Title: Machine Learning Basics
2. What is Machine Learning?
3. Types of ML
4. Supervised Learning
5. Unsupervised Learning
6. Neural Networks
7. Common Applications
8. Getting Started
9. Tools & Frameworks
10. Best Practices
11. Resources
12. Questions

### Download
- Local: `workspace/files/machine_learning_basics.pptx`
- [Download via S3](presigned-url)
```

## Templates

### Business Presentation
- Title slide with company logo
- Agenda
- Problem statement
- Solution overview
- Key benefits
- Implementation plan
- Timeline
- Budget
- Next steps
- Q&A

### Technical Overview
- Title
- Introduction
- Architecture diagram
- Components
- Data flow
- Security considerations
- Performance metrics
- Demo
- Conclusion

### Project Status
- Title
- Executive summary
- Progress overview
- Milestones achieved
- Current blockers
- Risks & mitigations
- Next sprint goals
- Resource needs
- Questions

## Error Handling

### Missing Dependencies
> "python-pptx is not installed. I can create the presentation once the dependency is added."

### Invalid Content
> "Some of the image paths provided don't exist. I'll create the presentation without those images and note which ones were missing."

### File Access
> "I couldn't save to that location. The presentation has been saved to workspace/files/ instead."

## MCP Servers

None required - uses python-pptx library directly.

## Dependencies

- `python-pptx>=0.6.23`

## Best Practices

1. **Keep slides simple**: Max 6 bullet points per slide
2. **Use visuals**: Add diagrams where possible
3. **Consistent styling**: Apply same fonts/colors throughout
4. **Clear hierarchy**: Title > Subtitle > Body > Notes
5. **Readable fonts**: Minimum 24pt for body text
