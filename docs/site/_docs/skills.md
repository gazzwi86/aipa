---
layout: doc
title: Creating Skills
nav_order: 5
---

Skills are capability modules that teach AIPA how to perform specific tasks.

## What is a Skill?

A skill is a folder containing:
- `SKILL.md` - Main instructions with YAML frontmatter
- Optional supporting files (scripts, templates, data)

Skills are loaded dynamically based on context and trigger keywords.

## Skill Structure

```
.claude/skills/
├── my-skill/
│   ├── SKILL.md
│   └── resources/        # Optional
│       ├── template.md
│       └── example.py
```

## Creating a Skill

### 1. Create the Directory

```bash
mkdir -p .claude/skills/my-skill
```

### 2. Create SKILL.md

```markdown
---
name: my-skill
description: What this skill does and when to use it
triggers:
  - keyword1
  - keyword2
  - context phrase
---

# My Skill

Instructions for Claude when this skill is active.

## When to Activate

- Situation 1
- Situation 2

## Guidelines

1. First guideline
2. Second guideline

## Examples

### Example 1: Basic Usage

```python
# Example code
```

## Resources

- Link to documentation
- Reference material
```

### 3. Test the Skill

Run Claude Code in your project and mention a trigger keyword.

## Frontmatter Reference

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Unique identifier (lowercase, hyphens) | Yes |
| `description` | What the skill does and when to use it | Yes |
| `triggers` | Keywords that activate the skill | Optional |

## Progressive Disclosure

Skills use a three-tier loading system:

1. **Metadata** (~100 tokens) - Name and description, always loaded
2. **Instructions** (<5k tokens) - Main content, loaded on activation
3. **Resources** - Supporting files, loaded on demand

This minimizes context usage while keeping capabilities available.

## Example Skills

### AWS Infrastructure

```markdown
---
name: aws-infrastructure
description: AWS infrastructure patterns and Terraform best practices
triggers:
  - terraform
  - aws
  - ecs
  - infrastructure
---

# AWS Infrastructure Skill

Patterns for AWS infrastructure using Terraform.

## When to Activate

- Working in `terraform/` directory
- Discussing AWS services
- Planning infrastructure changes

## Terraform Patterns

### Resource Naming
...
```

### TDD

```markdown
---
name: tdd
description: Test-Driven Development methodology - RED-GREEN-REFACTOR
triggers:
  - test
  - implement
  - feature
  - bug fix
---

# Test-Driven Development (TDD)

**Iron Law**: No production code without a failing test first.

## The RED-GREEN-REFACTOR Cycle

### 1. RED Phase
Write a failing test...
```

## Skill Categories

| Category | Examples |
|----------|----------|
| Development | `tdd`, `systematic-debugging`, `python-fastapi` |
| Infrastructure | `aws-infrastructure`, `docker-deployment` |
| Workflow | `git-workflow`, `github-actions`, `plan-execution` |
| Security | `security-hardening` |
| Meta | `skill-creator` |

## Best Practices

1. **Clear triggers** - Use specific keywords that indicate when the skill applies
2. **Actionable instructions** - Write as if explaining to a colleague
3. **Include examples** - Show concrete usage patterns
4. **Reference MCP servers** - List relevant tools for the skill
5. **Keep focused** - One skill per domain, don't overlap

## Automatic Activation

Skills activate automatically when:
- A trigger keyword appears in the conversation
- Working in a directory that matches the skill's domain
- The user explicitly mentions the skill

## Contributing Skills

See [CONTRIBUTING.md](https://github.com/gazzwi86/aipa/blob/main/CONTRIBUTING.md) for guidelines on submitting skills to the project.
