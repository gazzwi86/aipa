---
name: notion-enhanced
description: Advanced Notion operations for notes, projects, and knowledge management
triggers:
  - create note
  - update project
  - add to notion
  - notion database
  - link pages
  - organize notes
  - search notion
---

# Enhanced Notion Skill

Advanced Notion operations for knowledge management, projects, and notes beyond basic tasks.

## When to Activate

- "Create a note about..."
- "Update the project status for..."
- "Link this to the client..."
- "Search my notes for..."
- "Organize my research on..."
- "Create a project page for..."

## Capabilities

### Notes Management
- Create structured notes
- Apply templates
- Add to databases
- Link to projects/clients
- Tag and categorize
- Full-text search

### Project Management
- Create project pages
- Update status
- Link tasks, notes, clients
- Track milestones
- Generate reports

### Knowledge Base
- Research documentation
- Decision logs
- Meeting notes
- Reference materials
- Learnings capture

## MCP Server

Uses `notion` MCP server.

### Available Tools

```
notion_search          - Search across all pages
notion_get_page        - Get page content
notion_create_page     - Create new page in database
notion_update_page     - Update existing page
notion_query_database  - Query database with filters
notion_list_databases  - List all databases
```

## Database Structure

| Database | Purpose | Key Properties |
|----------|---------|----------------|
| Notes | Documentation, ideas | Title, Category, Created, Project |
| Tasks | Action items | Title, Status, Due, Priority, Project |
| Projects | Work initiatives | Title, Status, Client, Start/End |
| Clients | Client information | Name, Contact, Status |

### Note Categories
- Note (general documentation)
- Research (investigation findings)
- Thought/Idea (brainstorming)
- Meeting (meeting notes)
- Decision (decision log)

## Operations

### Create Note

```python
# 1. Find Notes database
databases = notion_list_databases()
notes_db = find_database(databases, "Notes")

# 2. Create note with properties
notion_create_page(
    database_id=notes_db["id"],
    properties={
        "Title": {"title": [{"text": {"content": "Research: AI Assistants"}}]},
        "Category": {"select": {"name": "Research"}},
        "Project": {"relation": [{"id": project_id}]}
    },
    content=[
        {
            "type": "heading_2",
            "content": "Summary"
        },
        {
            "type": "paragraph",
            "content": "Key findings from the research..."
        },
        {
            "type": "bulleted_list",
            "items": ["Finding 1", "Finding 2", "Finding 3"]
        }
    ]
)
```

### Update Project Status

```python
# 1. Find project
results = notion_query_database(
    database_id=projects_db_id,
    filter={"property": "Title", "title": {"contains": "Website Redesign"}}
)
project = results["results"][0]

# 2. Update status
notion_update_page(
    page_id=project["id"],
    properties={
        "Status": {"select": {"name": "In Progress"}},
        "Progress": {"number": 45}
    }
)
```

### Search Notes

```python
# Search across all content
results = notion_search(
    query="machine learning",
    filter={"property": "object", "value": "page"}
)

# Filter to Notes database
notes = [r for r in results if r["parent"]["database_id"] == notes_db_id]
```

### Link Related Content

```python
# Link note to project
notion_update_page(
    page_id=note_id,
    properties={
        "Project": {"relation": [{"id": project_id}]}
    }
)

# Link project to client
notion_update_page(
    page_id=project_id,
    properties={
        "Client": {"relation": [{"id": client_id}]}
    }
)
```

## Note Templates

### Research Note

```markdown
# [Topic] Research

## Summary
[Brief overview of findings]

## Key Points
- Point 1
- Point 2
- Point 3

## Sources
1. [Source 1](url)
2. [Source 2](url)

## Implications
[What this means for us]

## Next Steps
- [ ] Action 1
- [ ] Action 2

## Related
- [[Related Note 1]]
- [[Related Project]]
```

### Meeting Note

```markdown
# Meeting: [Subject]

**Date**: YYYY-MM-DD
**Attendees**: Person 1, Person 2

## Agenda
1. Topic 1
2. Topic 2

## Discussion
[Meeting notes]

## Decisions
- Decision 1
- Decision 2

## Action Items
| Action | Owner | Due |
|--------|-------|-----|
| Task 1 | Person | Date |

## Next Meeting
[Date and topics]
```

### Decision Log

```markdown
# Decision: [Title]

**Date**: YYYY-MM-DD
**Decision Maker**: [Name]
**Status**: Approved/Pending/Rejected

## Context
[Background and why this decision needed to be made]

## Options Considered
1. **Option A**: [Description]
   - Pros: ...
   - Cons: ...
2. **Option B**: [Description]
   - Pros: ...
   - Cons: ...

## Decision
[What was decided and why]

## Implications
- [Impact 1]
- [Impact 2]

## Review Date
[When to revisit this decision]
```

## Workflow Examples

### Daily Note

1. "Create today's daily note"
2. Find/create daily notes database
3. Create page with today's date
4. Apply daily template
5. Link to current projects

### Project Documentation

1. "Document the API design for the new feature"
2. Create note in Notes database
3. Category: "Note"
4. Link to project
5. Add structured content
6. Tag appropriately

### Research Capture

1. "Save this research about [topic]"
2. Create note with "Research" category
3. Structure findings
4. Add sources
5. Link to relevant project
6. Create follow-up tasks if needed

## Response Format

### Voice (Brief)
> "I've created a note about the API design and linked it to the Website Redesign project. You can find it in your Notes database."

### Text (Detailed)
```markdown
## Note Created

**Title**: API Design for User Authentication
**Database**: Notes
**Category**: Note
**Project**: Website Redesign

### Content
- Summary of design decisions
- Endpoint specifications
- Authentication flow diagram
- Security considerations

### Links
- Related to: Website Redesign project
- Tags: API, Authentication, Security

[View in Notion](notion-url)
```

## Database Discovery

On first use, discover database IDs:

```python
async def discover_databases():
    """Find and cache database IDs."""
    databases = await notion_list_databases()

    db_map = {}
    for db in databases:
        name = db["title"][0]["text"]["content"].lower()
        if "notes" in name:
            db_map["notes"] = db["id"]
        elif "tasks" in name:
            db_map["tasks"] = db["id"]
        elif "projects" in name:
            db_map["projects"] = db["id"]
        elif "clients" in name:
            db_map["clients"] = db["id"]

    return db_map
```

## Error Handling

### Database Not Found
> "I couldn't find a Notes database in your Notion workspace. Would you like me to create one?"

### Permission Denied
> "I don't have permission to access that page. Please check the Notion integration settings."

### Rate Limited
> "Notion API rate limit reached. I'll retry in a moment."

### Page Not Found
> "I couldn't find a project matching 'Website Redesign'. Here are similar projects: [list]"

## MCP Servers

- `notion` - Required for all Notion operations

## Integration

Works with:
- `notion-tasks` - For task management
- `deep-research` - Save research findings
- `claim-analyzer` - Document verified claims
- `meeting-notes` - Save meeting documentation

## Best Practices

1. **Consistent naming**: Use clear, searchable titles
2. **Always link**: Connect notes to projects/clients
3. **Use categories**: Proper categorization aids discovery
4. **Template usage**: Consistent structure across notes
5. **Regular review**: Archive or update stale notes
