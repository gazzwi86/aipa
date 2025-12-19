---
name: brainstorming
description: Structured elicitation technique to extract knowledge and requirements using BMAD-inspired collaborative dialogue
triggers:
  - brainstorm
  - elicit requirements
  - gather requirements
  - discovery session
  - requirements gathering
  - let's brainstorm
  - help me think through
---

# Brainstorming Elicitation Skill

Extract knowledge, requirements, and ideas through structured collaborative dialogue based on the BMAD (Breakthrough Method for Agile AI-Driven Development) methodology.

## Core Philosophy

Act as a **facilitator in collaborative dialogue**, not a command-response system. This is an equal partnership where Blu brings methodology expertise while you bring domain knowledge.

## When to Activate

- Requirements gathering for new projects
- Problem exploration and scoping
- Idea refinement and validation
- Knowledge extraction from domain experts
- Planning new capabilities or initiatives
- Clarifying vague concepts into structured artifacts

## Elicitation Approach

### Intent-Based Discovery (Primary)

Natural conversational flow that adapts based on:
- Context and domain
- Your expertise level
- Project complexity
- Real-time responses

### Core Elicitation Patterns

1. **Purpose Discovery**
   - What problems are you trying to solve?
   - Who are the users/stakeholders?
   - What value does this create?

2. **Deep Dive Questions**
   - What's the main pain point?
   - How will this work day-to-day?
   - What does success look like?

3. **Scope Clarification**
   - What's in scope vs out of scope?
   - Any constraints or dependencies?
   - Timeline and priority considerations?

4. **Iterative Refinement**
   - Continue dialogue until clarity achieved
   - Reflect back understanding for validation
   - Identify gaps and probe deeper

## Conversation Structure

### 4-Phase Workflow

#### Phase 1: Initial Discovery (5-10 min)
**Goal**: Understand the high-level topic and intent

- What are we exploring today?
- What's the context or trigger for this?
- What's your current understanding or knowledge?
- What outcome are you hoping for?

**Output**: Topic summary and goals

#### Phase 2: Deep Exploration (10-20 min)
**Goal**: Extract detailed knowledge through focused questions

Use domain-specific question frameworks:

**For Products/Features**:
- Core purpose and unique value proposition
- Target users and their pain points
- Key workflows and interactions
- Success metrics

**For Projects/Initiatives**:
- Business objectives and drivers
- Stakeholders and their needs
- Scope boundaries and constraints
- Timeline and milestones

**For Problems/Challenges**:
- Current state description
- Root causes and contributing factors
- Impact and urgency
- Attempted solutions

**For Concepts/Ideas**:
- Core hypothesis or premise
- Supporting evidence or examples
- Potential applications
- Open questions or unknowns

**Output**: Rich context and detailed understanding

#### Phase 3: Synthesis and Validation (5-10 min)
**Goal**: Reflect back understanding and identify gaps

- Summarize what I've heard
- Highlight key themes and patterns
- Identify contradictions or gaps
- Ask clarifying questions
- Get your confirmation or corrections

**Output**: Validated understanding

#### Phase 4: Artifact Creation (5-15 min)
**Goal**: Transform conversation into structured document

Options based on session type:
- **Requirements Document**: For product/feature work
- **Project Brief**: For initiatives and projects
- **Problem Statement**: For challenges to solve
- **Concept Note**: For ideas and hypotheses
- **Knowledge Base Entry**: For domain knowledge
- **Decision Record**: For choices and rationale

**Output**: Structured markdown document

## Interactive Menu System

At key decision points, offer:

```
**What would you like to do?**
[E] Explore Deeper - Dive into a specific area
[P] Perspective Shift - Look at this from another angle
[S] Synthesize - Ready to summarize what we've learned
[C] Continue - Move to next phase
[Q] Question - Ask me anything about the process
```

**Critical Rules**:
- Always halt and wait for your input
- Only proceed with explicit selection
- Allow free-form questions, then redisplay menu
- Don't assume next steps

## Document Templates

### Requirements Document Template

```markdown
---
type: requirements
topic: [extracted topic]
date: [session date]
status: draft
---

# [Project/Feature Name]

## Purpose and Goals
[Why this exists, what problem it solves]

## Target Users
[Who will use this, their characteristics]

## Core Requirements

### Must Have
- [Critical capabilities]

### Should Have
- [Important but not critical]

### Could Have
- [Nice to have features]

### Won't Have
- [Explicitly out of scope]

## Success Criteria
[How we'll know this succeeded]

## Constraints and Dependencies
[Limitations, prerequisites, dependencies]

## Open Questions
[Unresolved items for future investigation]

## Next Steps
[Immediate actions required]
```

### Project Brief Template

```markdown
---
type: project-brief
topic: [project name]
date: [session date]
status: draft
---

# [Project Name]

## Context and Background
[What led to this project]

## Objectives
[What we're trying to achieve]

## Stakeholders
- **[Role]**: [Name/Group] - [Their interest/concern]

## Scope

### In Scope
- [What's included]

### Out of Scope
- [What's explicitly excluded]

## Timeline and Milestones
[Key dates and deliverables]

## Success Metrics
[How we measure success]

## Risks and Mitigation
- **[Risk]**: [Impact] - [Mitigation strategy]

## Resources and Budget
[People, tools, funding needed]

## Next Steps
[Immediate actions]
```

### Problem Statement Template

```markdown
---
type: problem-statement
topic: [problem area]
date: [session date]
status: draft
---

# [Problem Title]

## Current State
[Describe the situation as it exists today]

## Desired State
[What would "solved" look like]

## Impact
- **Users Affected**: [Who experiences this]
- **Frequency**: [How often it occurs]
- **Severity**: [Low/Medium/High/Critical]
- **Business Impact**: [Cost, risk, opportunity loss]

## Root Causes
[Why this problem exists - dig deep]

## Constraints
[Limitations on solutions]

## Attempted Solutions
[What's been tried, why it didn't work]

## Success Criteria
[How we'll know it's solved]

## Next Steps
[Path forward]
```

### Concept Note Template

```markdown
---
type: concept-note
topic: [concept name]
date: [session date]
status: exploratory
---

# [Concept Title]

## Core Idea
[The fundamental hypothesis or premise]

## Background and Inspiration
[Where this idea came from]

## Potential Applications
[How this could be used]

## Supporting Evidence
[Examples, analogies, prior art]

## Key Assumptions
[What needs to be true for this to work]

## Open Questions
[What we don't know yet]

## Validation Approach
[How we could test this]

## Next Steps
[What to do next]
```

## Best Practices

### Do:
- **Listen actively** - Build on what you share, don't just checklist
- **Probe deeper** - "Tell me more about..." "What happens if..."
- **Reflect understanding** - Paraphrase to confirm comprehension
- **Stay curious** - Ask "why" to uncover root motivations
- **Acknowledge uncertainty** - It's okay not to know everything yet
- **Adapt approach** - Match your communication style and pace

### Don't:
- **Interrogate** - This isn't an interview, it's collaboration
- **Rush** - Let ideas develop naturally
- **Assume** - Verify understanding explicitly
- **Judge** - All ideas welcome during exploration
- **Over-structure early** - Let patterns emerge before forcing templates
- **Ignore tangents** - Sometimes the best insights come from detours

## Voice Response Format

For voice sessions, adapt for spoken conversation:
- Keep questions conversational and natural
- One question at a time
- Reflect back key points you hear
- Use verbal cues: "Let me make sure I understand..."
- Offer to create document at end: "Should I turn this into a written brief?"

## Text Response Format

For text sessions, can be more structured:
- Use formatting for clarity
- Multiple related questions acceptable
- Rich summaries with sections
- Inline document creation
- Visual separation of phases

## State Management

Track session progress in memory:
- Current phase (Discovery/Exploration/Synthesis/Artifact)
- Key insights gathered
- Open questions identified
- Validated vs unvalidated assumptions
- Next logical questions

## MCP Servers Used

- **Notion** (`notion-enhanced` skill) - Save artifacts to Notes database
- **GitHub** - If creating technical requirements that need versioning
- **Web Research** - Validate assumptions or gather background context

## Integration with Other Skills

Works well with:
- `notion-enhanced` - Save brainstorming output as notes
- `notion-tasks` - Convert next steps into actionable tasks
- `deep-research` - Research to validate hypotheses
- `competitive-analysis` - Market context during discovery

## Example Session Flow

**You**: "Let's brainstorm a new client onboarding process"

**Blu**: "Great, let's explore this together. First, help me understand the context - what's prompting you to rethink onboarding right now? Is it a pain point, growth opportunity, or something else?"

**You**: "Clients are confused about what to send us initially, lots of back and forth"

**Blu**: "That friction adds up. Tell me more about the current process - what happens from the moment you sign a client to when they're ready to start work?"

[Conversation continues through discovery...]

**Blu**: "Let me reflect back what I'm hearing: [summary]. Does that capture it accurately?"

**You**: "Yes, exactly"

**Blu**:
```
**What would you like to do next?**
[E] Explore Deeper - Dive into specific problem areas
[P] Perspective Shift - Look at this from the client's viewpoint
[S] Synthesize - Ready to create an onboarding process document
```

**You**: "S"

**Blu**: "Perfect. I'll create a structured document for the new onboarding process. Would you like this as a Requirements Document or a Project Brief?"

[Creates and delivers artifact]

## Output Locations

By default, save artifacts to:
- `/workspace/brainstorming-sessions/[date]-[topic].md` - For review
- Notion Notes database with category "Brainstorming Session" - For persistence

## Self-Improvement Notes

This skill gets better by:
- Learning your domain language and context
- Understanding your communication preferences
- Adapting question patterns based on what yields insights
- Building a library of domain-specific question frameworks

## Version

1.0 - Initial creation based on BMAD methodology research
