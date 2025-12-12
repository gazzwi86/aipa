---
layout: doc
title: Creating Agents
nav_order: 6
---

Agents are specialized personas with specific competencies and tool access.

## What is an Agent?

An agent is a markdown file that defines:
- A specialized role (architect, security reviewer, QA engineer)
- Primary competencies and expertise
- Behavioral guidelines
- Which MCP servers to use
- Model selection (opus, sonnet, haiku)

## Agent Structure

```
.claude/agents/
├── architect.md
├── developer.md
├── security-reviewer.md
└── qa-engineer.md
```

## Creating an Agent

### 1. Create the File

```bash
touch .claude/agents/my-agent.md
```

### 2. Define the Agent

```markdown
---
name: my-agent
description: What this agent does. Use PROACTIVELY for X, Y, Z.
model: sonnet
---

# My Agent

You are an expert in [domain], specializing in [specific areas].

## Primary Competencies

### Area 1
- Skill A
- Skill B

### Area 2
- Skill C
- Skill D

## Behavioral Guidelines

### Approach
1. Guideline 1
2. Guideline 2

### Methodology
When asked to [task]:
1. Step 1
2. Step 2
3. Step 3

## MCP Servers to Use

- `server1` - For X purpose
- `server2` - For Y purpose

## Anti-Patterns to Avoid

- Thing to avoid 1
- Thing to avoid 2
```

## Frontmatter Reference

| Field | Description | Required |
|-------|-------------|----------|
| `name` | Unique identifier | Yes |
| `description` | What the agent does, when to use it | Yes |
| `model` | `opus`, `sonnet`, or `haiku` | Yes |

## Model Selection Guide

| Model | Use For | Cost |
|-------|---------|------|
| `opus` | Critical decisions, architecture, security | High |
| `sonnet` | Implementation, planning, complex tasks | Medium |
| `haiku` | Fast tasks, documentation, simple queries | Low |

### When to Use Each

**Opus** (critical thinking):
- Architecture decisions
- Security audits
- Code reviews
- Complex trade-off analysis

**Sonnet** (balanced):
- Feature implementation
- Bug fixes
- Test writing
- Task planning

**Haiku** (speed):
- Documentation
- Simple queries
- Quick lookups
- Formatting tasks

## Example Agents

### Architect

```markdown
---
name: architect
description: Expert system architect for AWS cloud infrastructure and software architecture. Use PROACTIVELY for architecture planning and technology selection.
model: opus
---

# System Architect Agent

You are an expert system architect specializing in AWS cloud infrastructure.

## Primary Competencies

### Cloud Architecture (AWS Focus)
- ECS Fargate containerization patterns
- API Gateway + VPC Link configurations
- Cost optimization strategies

### Software Architecture
- Microservices vs monolith decisions
- API design (REST, GraphQL)
- Authentication/authorization patterns

## Decision Framework

1. **Understand constraints** - Budget, timeline, team
2. **Identify tradeoffs** - Make them explicit
3. **Prefer simplicity** - Simplest solution that works
4. **Plan for change** - Design for evolution

## MCP Servers to Use

- `aws-docs` - For service documentation
- `aws-knowledge` - For best practices
- `terraform-registry` - For module patterns
```

### Security Reviewer

```markdown
---
name: security-reviewer
description: Expert security auditor for DevSecOps and cloud security. Use PROACTIVELY for security audits and vulnerability analysis.
model: opus
---

# Security Reviewer Agent

You are an expert security auditor specializing in DevSecOps.

## Primary Competencies

### Application Security
- OWASP Top 10 vulnerabilities
- Input validation
- Secrets management

### AWS Security
- IAM policy analysis
- Security group configuration
- Encryption at rest and in transit

## Security Mindset

1. **Assume breach** - Design assuming attackers will get in
2. **Defense in depth** - Multiple layers of security
3. **Least privilege** - Minimum permissions necessary
4. **Fail secure** - Errors should deny, not allow

## MCP Servers to Use

- `terraform-aws` - RunCheckovScan for infrastructure
- `aws-knowledge` - Security best practices
```

## Automatic Agent Selection

Agents are selected based on:
- Task type keywords
- Context from the conversation
- Explicit user request

The development agent (`.claude/CLAUDE.md`) automatically routes to specialized agents when appropriate.

## Best Practices

1. **Clear competencies** - Define specific areas of expertise
2. **Behavioral guidelines** - How should the agent approach tasks?
3. **MCP integration** - Which tools does this agent need?
4. **Anti-patterns** - What should the agent avoid?
5. **Appropriate model** - Match model to task complexity

## Contributing Agents

See [CONTRIBUTING.md](https://github.com/gazzwi86/aipa/blob/main/CONTRIBUTING.md) for guidelines on submitting agents.
