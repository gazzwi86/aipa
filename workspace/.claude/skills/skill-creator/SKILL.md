---
name: skill-creator
description: Create new skills and agents for Blu
triggers:
  - create skill
  - new skill
  - add skill
  - I need a skill
---

# Skill Creator Skill

Create new capabilities for Blu.

## When to Activate

- "Create a skill for..."
- "Add a skill that..."
- "I need a skill to..."
- Repeated workflow identified

## Skill Structure

```
.claude/skills/{skill-name}/
├── SKILL.md           # Required
└── [supporting files]
```

## SKILL.md Template

```markdown
---
name: skill-name
description: Brief description
triggers:
  - activation keyword 1
  - activation phrase 2
---

# Skill Name

What this skill does.

## When to Activate

Specific scenarios.

## Workflow

Steps this skill performs.

## Voice Response Format

How to respond briefly.

## Text Response Format

How to respond in detail.

## MCP Servers

- `server` - Purpose
```

## Creation Workflow

1. **Identify the need** - What repeated task or capability?
2. **Name it** - Clear, kebab-case name
3. **Define triggers** - What phrases activate it?
4. **Document workflow** - What does it do?
5. **Create SKILL.md** - Write the file
6. **Test** - Verify activation works

## Good Skill Candidates

- Repeated workflows (>3 times)
- Multi-step processes
- Integration patterns
- Domain-specific knowledge

## Bad Skill Candidates

- One-time tasks
- Simple lookups
- Generic capabilities

## Self-Improvement

When you identify a capability gap:
1. Note the pattern
2. Propose a skill
3. Get approval
4. Create and document
5. Git hook auto-commits
