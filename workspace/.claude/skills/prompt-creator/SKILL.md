---
name: prompt-creator
description: Generate effective prompts based on requirements
triggers:
  - create prompt
  - generate prompt
  - write prompt
  - prompt for
  - help me prompt
---

# Prompt Creator Skill

Generate effective prompts for various AI use cases.

## When to Activate

- "Create a prompt for..."
- "Write a prompt that..."
- "Help me prompt Claude to..."
- "Generate a system prompt for..."

## Capabilities

### Prompt Types
- System prompts (for AI assistants)
- Task prompts (single-use)
- Chain-of-thought prompts
- Few-shot prompts
- Structured output prompts

### Optimization
- Clear instructions
- Proper formatting
- Examples when helpful
- Output constraints

## Prompt Templates

### System Prompt Template
```markdown
# IDENTITY
You are [role] with expertise in [domains].

# CONTEXT
[Background information needed]

# INSTRUCTIONS
[Step-by-step instructions]

# CONSTRAINTS
[What to avoid or limitations]

# OUTPUT FORMAT
[Expected format of response]
```

### Task Prompt Template
```markdown
# TASK
[Clear description of what to do]

# INPUT
[The data/content to process]

# REQUIREMENTS
- [Requirement 1]
- [Requirement 2]

# OUTPUT
[Expected output format]
```

### Few-Shot Template
```markdown
# TASK
[Description]

# EXAMPLES

Input: [example 1 input]
Output: [example 1 output]

Input: [example 2 input]
Output: [example 2 output]

# NOW PROCESS

Input: [actual input]
Output:
```

## Creation Process

### 1. Understand Goal
- What should the AI accomplish?
- What's the desired output?
- What constraints exist?

### 2. Define Role
- What expertise is needed?
- What perspective should be taken?

### 3. Structure Instructions
- Break into clear steps
- Be specific, not vague
- Include examples if helpful

### 4. Specify Output
- Format (markdown, JSON, etc.)
- Length constraints
- Quality criteria

### 5. Add Guardrails
- What to avoid
- Edge cases to handle
- Safety considerations

## Prompt Quality Checklist

- [ ] Clear, specific instructions
- [ ] Appropriate role/identity
- [ ] Relevant context provided
- [ ] Output format specified
- [ ] Constraints defined
- [ ] Examples if needed
- [ ] No ambiguity

## Response Format

### Voice (Brief)
> "Here's a system prompt for a code reviewer. It sets up the AI as a senior developer who focuses on security, performance, and maintainability. Should I adjust the focus areas?"

### Text (Detailed)
```markdown
## Generated Prompt

### System Prompt: Code Review Assistant

```
# IDENTITY
You are a senior software engineer with 15 years of experience across multiple languages and frameworks. You specialize in code review with focus on security, performance, and maintainability.

# INSTRUCTIONS
When reviewing code:
1. First, understand the purpose of the change
2. Check for security vulnerabilities
3. Evaluate performance implications
4. Assess maintainability and readability
5. Suggest improvements with explanations

# OUTPUT FORMAT
Structure your review as:
- Summary (1-2 sentences)
- Security Issues (if any)
- Performance Issues (if any)
- Suggestions (prioritized list)
- Positive Notes (what's done well)

# CONSTRAINTS
- Be constructive, not critical
- Explain the "why" behind suggestions
- Prioritize by severity
- Don't nitpick style unless asked
```

### Usage Notes
- Works best with code diffs or full files
- Can be used with any programming language
- Adjust focus areas based on your needs
```

## Common Prompt Patterns

### Expert Role
> "You are an expert [X] with [Y] years of experience..."

### Step-by-Step
> "Follow these steps exactly: 1... 2... 3..."

### Output Constraint
> "Respond only in JSON format: {field1: string, field2: number}"

### Tone Setting
> "Be concise and direct. Avoid unnecessary words."

### Example-Driven
> "Here's an example of good output: [example]"

## MCP Servers

None required.

## Quality Guidelines

1. **Clarity over cleverness**: Simple is better
2. **Specific over general**: Details help
3. **Structure over prose**: Formatted prompts work better
4. **Test and iterate**: Try the prompt, refine
5. **Match to model**: Different models need different approaches
