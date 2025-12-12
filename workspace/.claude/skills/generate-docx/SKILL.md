---
name: generate-docx
description: Create Word documents programmatically
triggers:
  - create document
  - generate docx
  - write document
  - word document
  - create report
  - draft document
---

# Word Document Generation Skill

Create professional Word documents programmatically using python-docx.

## When to Activate

- "Create a document about..."
- "Write a report on..."
- "Generate a Word doc for..."
- "Draft a proposal for..."
- "Create meeting notes template"

## Capabilities

### Document Types
- Reports
- Proposals
- Meeting notes
- Technical documentation
- Letters
- Contracts
- Policies
- SOPs

### Formatting
- Headings (H1-H6)
- Paragraphs
- Bullet lists
- Numbered lists
- Tables
- Images
- Headers/footers
- Page breaks
- Table of contents

### Styling
- Custom fonts
- Colors
- Bold, italic, underline
- Alignment
- Line spacing
- Margins

## Implementation

### Basic Document

```python
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

def create_document(title: str, content: list[dict]) -> str:
    """Create a Word document.

    Args:
        title: Document title
        content: List of content blocks

    Returns:
        Path to generated .docx file
    """
    doc = Document()

    # Set document properties
    doc.core_properties.title = title
    doc.core_properties.author = "Ultra (AIPA)"

    # Add title
    heading = doc.add_heading(title, level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Add content blocks
    for block in content:
        add_content_block(doc, block)

    # Save
    filename = f"workspace/files/{title.lower().replace(' ', '_')}.docx"
    doc.save(filename)
    return filename
```

### Content Block Format

```python
content = [
    {
        "type": "heading",
        "level": 1,
        "text": "Executive Summary"
    },
    {
        "type": "paragraph",
        "text": "This document outlines the key findings...",
        "style": "normal"
    },
    {
        "type": "bullets",
        "items": [
            "First key point",
            "Second key point",
            "Third key point"
        ]
    },
    {
        "type": "numbered",
        "items": [
            "Step one",
            "Step two",
            "Step three"
        ]
    },
    {
        "type": "table",
        "headers": ["Name", "Role", "Department"],
        "rows": [
            ["Alice", "Engineer", "Tech"],
            ["Bob", "Designer", "UX"]
        ]
    },
    {
        "type": "image",
        "path": "workspace/files/diagram.png",
        "caption": "System Architecture",
        "width": 6  # inches
    },
    {
        "type": "page_break"
    }
]
```

### Add Content Block

```python
def add_content_block(doc, block: dict):
    """Add a content block to the document."""
    block_type = block.get("type")

    if block_type == "heading":
        doc.add_heading(block["text"], level=block.get("level", 1))

    elif block_type == "paragraph":
        p = doc.add_paragraph(block["text"])
        if block.get("style") == "quote":
            p.style = "Quote"

    elif block_type == "bullets":
        for item in block["items"]:
            doc.add_paragraph(item, style="List Bullet")

    elif block_type == "numbered":
        for item in block["items"]:
            doc.add_paragraph(item, style="List Number")

    elif block_type == "table":
        table = doc.add_table(rows=1, cols=len(block["headers"]))
        table.style = "Table Grid"

        # Header row
        for i, header in enumerate(block["headers"]):
            table.rows[0].cells[i].text = header

        # Data rows
        for row_data in block["rows"]:
            row = table.add_row()
            for i, cell_data in enumerate(row_data):
                row.cells[i].text = str(cell_data)

    elif block_type == "image":
        doc.add_picture(block["path"], width=Inches(block.get("width", 6)))
        if block.get("caption"):
            p = doc.add_paragraph(block["caption"])
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    elif block_type == "page_break":
        doc.add_page_break()
```

### Document Templates

```python
def create_report_template(title: str, sections: list[str]) -> list[dict]:
    """Generate content blocks for a report."""
    content = []

    # Executive summary placeholder
    content.append({"type": "heading", "level": 1, "text": "Executive Summary"})
    content.append({"type": "paragraph", "text": "[Executive summary content]"})

    # Sections
    for section in sections:
        content.append({"type": "heading", "level": 1, "text": section})
        content.append({"type": "paragraph", "text": f"[{section} content]"})

    # Appendix
    content.append({"type": "page_break"})
    content.append({"type": "heading", "level": 1, "text": "Appendix"})

    return content

def create_meeting_notes_template(meeting_title: str, attendees: list[str]) -> list[dict]:
    """Generate content blocks for meeting notes."""
    return [
        {"type": "heading", "level": 1, "text": "Meeting Details"},
        {"type": "paragraph", "text": f"**Date**: {datetime.now().strftime('%Y-%m-%d')}"},
        {"type": "paragraph", "text": f"**Subject**: {meeting_title}"},
        {"type": "heading", "level": 2, "text": "Attendees"},
        {"type": "bullets", "items": attendees},
        {"type": "heading", "level": 1, "text": "Agenda"},
        {"type": "numbered", "items": ["[Agenda item 1]", "[Agenda item 2]"]},
        {"type": "heading", "level": 1, "text": "Discussion"},
        {"type": "paragraph", "text": "[Meeting discussion notes]"},
        {"type": "heading", "level": 1, "text": "Action Items"},
        {"type": "table", "headers": ["Action", "Owner", "Due Date"], "rows": []},
        {"type": "heading", "level": 1, "text": "Next Meeting"},
        {"type": "paragraph", "text": "[Next meeting date and topics]"}
    ]
```

## Workflow

### From Request

1. User: "Create a project proposal for the new website"
2. Determine document type (proposal)
3. Generate outline
4. Fill in content
5. Save and return file path

### From Outline

1. User provides section headings
2. Convert to content blocks
3. Generate document
4. Return file path

### From Content

1. User provides raw text
2. Parse and structure
3. Apply formatting
4. Generate document
5. Return file path

## Response Format

### Voice (Brief)
> "I've created a 5-page project proposal document. It includes an executive summary, project scope, timeline, budget, and next steps. The file is saved to your workspace."

### Text (Detailed)
```markdown
## Document Created

**File**: `workspace/files/project_proposal_website.docx`
**Pages**: 5 (estimated)

### Contents
1. Executive Summary
2. Project Overview
3. Scope & Deliverables
4. Timeline
5. Budget Estimate
6. Team & Resources
7. Risks & Mitigations
8. Next Steps

### Download
- Local: `workspace/files/project_proposal_website.docx`
- [Download via S3](presigned-url)

### Notes
- Budget figures are placeholders - please review
- Timeline assumes Q1 start date
```

## Document Templates

### Proposal
- Executive summary
- Problem statement
- Proposed solution
- Scope
- Timeline
- Budget
- Team
- Conclusion

### Technical Spec
- Overview
- Requirements
- Architecture
- API specification
- Data models
- Security considerations
- Testing plan
- Deployment

### Meeting Notes
- Meeting details
- Attendees
- Agenda
- Discussion
- Decisions made
- Action items
- Next meeting

### Status Report
- Period covered
- Highlights
- Progress summary
- Risks/issues
- Next period plans
- Metrics

## Error Handling

### Missing Dependencies
> "python-docx is not installed. I can create the document once the dependency is added."

### Invalid Content
> "Some of the image paths provided don't exist. I'll create the document without those images."

### File Access
> "I couldn't save to that location. The document has been saved to workspace/files/ instead."

## MCP Servers

None required - uses python-docx library directly.

## Dependencies

- `python-docx>=1.1.0`

## Best Practices

1. **Clear structure**: Use headings hierarchy consistently
2. **Readable formatting**: Appropriate spacing and margins
3. **Visual breaks**: Use page breaks between major sections
4. **Tables for data**: Structure complex information in tables
5. **Consistent styling**: Apply same fonts throughout
