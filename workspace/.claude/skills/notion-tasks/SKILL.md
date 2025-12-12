---
name: notion-tasks
description: Task and project management via Notion
triggers:
  - create task
  - add task
  - add to my list
  - remind me
  - what's on my list
  - todo
  - tasks
---

# Notion Tasks Skill

Manage tasks and projects in Notion.

## When to Activate

- "Create a task to..."
- "Add X to my list"
- "Remind me to..."
- "What tasks do I have?"
- "What's due today?"

## Notion Structure

| Database | Properties |
|----------|------------|
| Tasks | Title, Status, Due Date, Priority, Project |
| Projects | Name, Status, Client |

### Task Status Values
- Not Started
- In Progress
- Done

### Priority Values
- P0 (Critical)
- P1 (High)
- P2 (Medium)
- P3 (Low)

## Operations

### Create Task
```
User: "Create a task to review the proposal by Friday"

Action:
1. Extract: title="Review the proposal", due="Friday"
2. Create in Tasks database
3. Confirm briefly
```

### List Tasks
```
User: "What's on my list today?"

Action:
1. Query Tasks where due_date = today
2. Format as brief list
3. Mention count
```

### Complete Task
```
User: "Mark the proposal review as done"

Action:
1. Find task by title match
2. Update status to "Done"
3. Confirm
```

## Voice Response Format

**Creating:**
> "Done. Task created for Friday."

**Listing:**
> "You have 3 tasks today: review proposal, call client, and update budget."

**Completing:**
> "Marked 'Review proposal' as done."

## MCP Server

- `notion` - All task operations

## Error Handling

- Task not found: "I couldn't find a task matching that. Did you mean...?"
- Multiple matches: "I found several tasks. Which one: A, B, or C?"
