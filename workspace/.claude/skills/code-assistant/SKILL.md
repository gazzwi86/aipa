---
name: code-assistant
description: Help with code questions, debugging, and snippets
triggers:
  - code
  - debug
  - error
  - how do I code
  - write a script
  - programming
---

# Code Assistant Skill

Help with code questions and debugging.

## When to Activate

- "How do I [code task]?"
- "Debug this error..."
- "Write a script to..."
- Code-related questions
- Error messages shared

## Capabilities

- Explain code
- Debug errors
- Write snippets
- Suggest improvements
- Answer programming questions

## Response Format

### Voice (Brief)
> "The error is because X. Change Y to Z to fix it."

### Text (Detailed)
```markdown
## Problem
What's happening.

## Cause
Why it's happening.

## Solution
```python
# Fixed code
```

## Explanation
Why this fixes it.
```

## Common Languages

- Python (primary)
- JavaScript/TypeScript
- Bash/Shell
- SQL
- Terraform/HCL

## Error Handling Workflow

1. Read the error message
2. Identify the root cause
3. Explain clearly
4. Provide fix
5. Explain prevention

## MCP Servers

- `github` - Code context
- `context7` - Library documentation

## Limitations

For major development work:
- This is for assistance, not full implementation
- Complex features should use development workflows
- Security-sensitive code needs review
