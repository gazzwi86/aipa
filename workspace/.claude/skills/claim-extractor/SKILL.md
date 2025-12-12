---
name: claim-extractor
description: Extract factual claims from content (Fabric-style)
triggers:
  - extract claims
  - what claims
  - list claims
  - fact check
  - claims in this
---

# Claim Extractor Skill

Extract factual claims from content for analysis and fact-checking.

## When to Activate

- "Extract the claims from this article"
- "What claims does this video make?"
- "List the factual assertions"
- "What needs fact-checking here?"

## Capabilities

### Claim Identification
Identify statements that:
- Assert facts (can be verified)
- Make predictions
- Cite statistics or data
- Reference studies or research
- Make causal claims

### Claim Classification
Categorize claims as:
- **Factual**: Can be objectively verified
- **Opinion**: Subjective statement
- **Prediction**: Future-oriented claim
- **Statistical**: Involves numbers/data
- **Causal**: Asserts cause-effect relationship
- **Expert**: Attributed to authority

### Source Attribution
Track where each claim originates.

## Extraction Process

### 1. Parse Content
Read through the entire content to understand context.

### 2. Identify Claims
Look for:
- Declarative statements
- "Studies show..."
- "Research indicates..."
- Numerical assertions
- Cause-effect statements
- Historical facts
- Scientific claims

### 3. Filter Non-Claims
Exclude:
- Questions
- Pure opinions without factual basis
- Hypotheticals clearly marked
- Jokes/hyperbole

### 4. Categorize
Assign type and confidence to each claim.

## Output Format

### Claim List

```markdown
## Extracted Claims

### Factual Claims
1. **Claim**: "Electric vehicles now outsell gas cars in Norway"
   - **Type**: Factual/Statistical
   - **Source**: Paragraph 3
   - **Verifiable**: Yes
   - **Confidence**: High (specific, measurable)

2. **Claim**: "Battery costs have dropped 90% since 2010"
   - **Type**: Statistical
   - **Source**: Paragraph 5
   - **Verifiable**: Yes
   - **Confidence**: High (specific, with timeframe)

### Causal Claims
3. **Claim**: "Government subsidies are the main reason for EV adoption"
   - **Type**: Causal
   - **Source**: Paragraph 7
   - **Verifiable**: Partially (correlation vs causation)
   - **Confidence**: Medium

### Predictions
4. **Claim**: "All new cars will be electric by 2035"
   - **Type**: Prediction
   - **Source**: Paragraph 10
   - **Verifiable**: Future
   - **Confidence**: N/A (prediction)

### Summary
- Total claims extracted: 12
- Factual: 6
- Statistical: 3
- Causal: 2
- Predictions: 1
```

## Response Format

### Voice (Brief)
> "I found 12 claims in this article. The main ones are: first, EVs now outsell gas cars in Norway; second, battery costs dropped 90% since 2010; and third, the author predicts all new cars will be electric by 2035. Want me to fact-check any of these?"

### Text (Detailed)
Full claim list as shown above.

## Fabric Pattern (Adapted)

Based on Fabric's `extract_claims` pattern:

```
# IDENTITY
You are an expert at extracting factual claims from content.

# STEPS
1. Read the entire content carefully
2. Identify every statement that makes a factual assertion
3. Exclude opinions, questions, and hypotheticals
4. Categorize each claim by type
5. Note the source location for each claim
6. Assess verifiability of each claim

# OUTPUT
- List each claim on its own line
- Include the claim type
- Note source location
- Indicate verifiability
```

## MCP Servers

None required - pure text analysis.

## Quality Guidelines

1. **Be thorough**: Capture all substantive claims
2. **Be precise**: Quote or paraphrase accurately
3. **Be fair**: Don't misrepresent context
4. **Be useful**: Focus on significant claims
5. **Be clear**: Distinguish fact from opinion

## Follow-up Actions

After extraction, offer:
- "Want me to verify any of these claims?"
- "Should I save this to your Notes?"
- "Want a summary of the strongest claims?"
