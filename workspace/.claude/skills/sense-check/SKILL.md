---
name: sense-check
description: Review requests and responses for quality and validity
triggers:
  - check this
  - review response
  - confidence score
  - sense check
  - does this make sense
  - verify my answer
  - quality check
---

# Sense Check Skill

Review and validate requests and responses for quality, accuracy, and completeness.

## When to Activate

- "Does this response make sense?"
- "Check my answer for errors"
- "How confident are you in this?"
- "Sense check this plan"
- "Review what you just said"

## Capabilities

### Response Validation
- Logical consistency
- Factual accuracy (where verifiable)
- Completeness
- Relevance to question

### Confidence Scoring
Rate confidence on responses:
- **High**: Well-supported, verified facts
- **Medium**: Reasonable but unverified
- **Low**: Uncertain, needs verification

### Quality Checks
- Grammar and clarity
- Code correctness
- Data accuracy
- Methodology soundness

## Review Framework

### 1. Logical Consistency
- Does the reasoning follow?
- Are there contradictions?
- Are assumptions stated?

### 2. Factual Accuracy
- Are claims verifiable?
- Are sources cited?
- Is data current?

### 3. Completeness
- Is the question fully answered?
- Are edge cases considered?
- Is context provided?

### 4. Relevance
- Does it address the actual question?
- Is there unnecessary information?
- Is the scope appropriate?

## Confidence Levels

### High Confidence
- Based on verified facts
- Multiple sources confirm
- Within domain expertise
- Clear methodology

### Medium Confidence
- Based on reasonable assumptions
- Limited verification available
- Some uncertainty exists
- Partial information

### Low Confidence
- Uncertain or speculative
- No verification possible
- Outside expertise
- Conflicting information

### Unable to Assess
- Subjective matter
- Future predictions
- Insufficient context

## Output Format

```markdown
## Sense Check Results

### Original Response
[Summary of what was reviewed]

### Assessment

**Confidence Level**: Medium

**Logical Consistency**: PASS
- Reasoning follows logically
- No contradictions found

**Factual Accuracy**: PARTIAL
- Claim 1: Verified ✓
- Claim 2: Unable to verify ⚠️
- Claim 3: Appears inaccurate ✗

**Completeness**: PASS
- Main question answered
- Edge cases mentioned

**Relevance**: PASS
- Directly addresses question

### Issues Found
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Suggestion for improvement]
2. [Suggestion for improvement]

### Summary
[Brief overall assessment]
```

## Response Format

### Voice (Brief)
> "I've reviewed my response. Confidence is medium - the technical parts are solid but I couldn't verify the specific statistics. The main risk is the cost estimate might be outdated. Want me to double-check those numbers?"

### Text (Detailed)
Full assessment as shown in format above.

## Self-Review Triggers

Automatically apply sense-check when:
- Response involves numbers/statistics
- Making recommendations
- Providing instructions for critical tasks
- Response seems uncertain
- User asks follow-up questions

## Quality Checklist

Before finalizing important responses:
- [ ] Answer addresses the actual question
- [ ] Claims are supported or flagged as uncertain
- [ ] Numbers/dates are verified or estimated
- [ ] Code has been tested (if applicable)
- [ ] Instructions are complete and safe
- [ ] Tone is appropriate

## Common Issues to Catch

1. **Hallucinated facts**: Statistics that seem specific but aren't verified
2. **Outdated information**: Things that may have changed
3. **Overgeneralization**: Claims that are too broad
4. **Missing caveats**: Important limitations not mentioned
5. **Circular reasoning**: Arguments that assume what they prove
6. **False precision**: Numbers more specific than warranted

## MCP Servers

None required - internal analysis.

## Integration

Can be called:
- Manually: "Sense check this"
- Automatically: After complex responses
- As a pipeline: Review before sending important communications

## Response Patterns

### High Confidence Response
> "I'm confident in this answer. It's based on official AWS documentation and I've verified the syntax."

### Medium Confidence Response
> "This answer is based on common patterns but I haven't verified the specific version compatibility. Consider testing first."

### Low Confidence Response
> "I'm not certain about this. The information might be outdated. I'd recommend verifying with the official source before proceeding."
