---
name: claim-analyzer
description: Analyze claims for validity and evidence
triggers:
  - analyze claims
  - verify claims
  - check validity
  - fact check this
  - is this true
---

# Claim Analyzer Skill

Analyze extracted claims for validity, find supporting/contradicting evidence.

## When to Activate

- "Analyze these claims"
- "Verify if this is true"
- "Fact check this statement"
- "Is this claim accurate?"
- "Find evidence for/against..."

## Capabilities

### Evidence Search
Search for supporting or contradicting evidence from:
- Official sources
- Academic papers
- News articles
- Expert opinions
- Statistical databases

### Validity Assessment
Rate claims on a scale:
- **Verified**: Strong evidence supports
- **Likely True**: Partial evidence supports
- **Uncertain**: Insufficient evidence
- **Likely False**: Evidence contradicts
- **False**: Strong evidence contradicts
- **Unverifiable**: Cannot be checked

### Bias Detection
Identify potential:
- Source bias
- Cherry-picked data
- Missing context
- Logical fallacies

## Analysis Process

### 1. Understand the Claim
- What exactly is being asserted?
- What would prove/disprove it?
- What's the implicit context?

### 2. Search for Evidence
- Primary sources first
- Multiple independent sources
- Recent vs historical data
- Expert consensus

### 3. Evaluate Evidence
- Source credibility
- Data quality
- Methodological soundness
- Potential conflicts of interest

### 4. Form Assessment
- Weigh evidence for/against
- Note confidence level
- Acknowledge limitations

## Output Format

```markdown
## Claim Analysis

### Claim
"Battery costs have dropped 90% since 2010"

### Assessment: VERIFIED

### Evidence

**Supporting:**
1. BloombergNEF Report (2023)
   - "Lithium-ion battery pack prices fell 89% from 2010 to 2022"
   - Source: [URL]
   - Credibility: High (industry standard source)

2. US Department of Energy
   - "Battery costs declined from $1,100/kWh to $143/kWh"
   - Source: [URL]
   - Credibility: High (government source)

**Contradicting:**
- None found

### Confidence: HIGH

### Notes
- Slight variation in exact percentages (89-91%)
- Refers to pack-level costs, not cell-level
- 2024 data may show different figures due to lithium price fluctuations

### Conclusion
The claim is accurate. Multiple authoritative sources confirm roughly 90% cost reduction in lithium-ion batteries from 2010 to 2022-2023.
```

## Validity Ratings

| Rating | Definition | Confidence |
|--------|------------|------------|
| Verified | Multiple reliable sources confirm | High |
| Likely True | Some evidence supports, no contradictions | Medium-High |
| Uncertain | Mixed evidence or limited data | Low |
| Likely False | Evidence tends to contradict | Medium-High |
| False | Multiple sources contradict | High |
| Unverifiable | No way to check (opinion, future) | N/A |

## Response Format

### Voice (Brief)
> "I checked the battery cost claim - it's verified. Bloomberg and the Department of Energy both confirm about 90% cost reduction since 2010. The exact figure varies between 89-91% depending on the source."

### Text (Detailed)
Full analysis as shown above.

## Fabric Pattern (Adapted)

Based on Fabric's approach to claim analysis:

```
# IDENTITY
You are an expert fact-checker with access to web search.

# STEPS
1. Parse the claim precisely
2. Identify what evidence would verify/refute it
3. Search for authoritative sources
4. Evaluate source credibility
5. Weigh evidence objectively
6. Provide assessment with confidence level

# OUTPUT
- Clear verdict
- Supporting evidence with citations
- Contradicting evidence if any
- Confidence level
- Caveats and context
```

## MCP Servers

- `playwright` - Web search for evidence
- `aws-docs` - For AWS-related claims
- `context7` - Technical documentation

## Quality Guidelines

1. **Be thorough**: Check multiple sources
2. **Be balanced**: Present both sides
3. **Be transparent**: Show reasoning
4. **Be humble**: Acknowledge uncertainty
5. **Be fair**: Don't cherry-pick evidence

## Common Pitfalls

- Confirmation bias in searching
- Over-reliance on single source
- Ignoring context
- False precision
- Missing nuance

## Follow-up

After analysis:
- "Want me to check another claim?"
- "Should I research this topic more deeply?"
- "Save this analysis to your Notes?"
