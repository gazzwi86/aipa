---
name: meeting-notes
description: Extract structured meeting notes from transcripts
triggers:
  - meeting notes
  - save meeting
  - summarize the meeting
  - meeting summary
  - extract action items
  - what were the decisions
  - meeting recap
---

# Meeting Notes Skill

Extract structured notes from meeting transcripts including action items, decisions, key takeaways, and commitments.

## When to Activate

- "Here's the meeting transcript, create notes"
- "Summarize this meeting"
- "What were the action items from the meeting?"
- "Meeting recap please"
- After a VoiceMode call ends with meeting content

## Input Sources

| Source | How |
|--------|-----|
| Pasted transcript | User pastes text |
| VoiceMode call | Transcript from completed call |
| Audio file | Transcribe first, then process |
| Document | Read file, extract meeting content |

## Output Template

```markdown
# Meeting: [Title or Topic]

**Date**: YYYY-MM-DD | **Duration**: ~X min
**Attendees**: [Names if mentioned]
**Next Meeting**: [Date/time if scheduled]

## Key Takeaways
1. [Main point 1]
2. [Main point 2]
3. [Main point 3]

## Decisions Made
| Decision | Context | Owner |
|----------|---------|-------|
| [What was decided] | [Why/background] | [Who owns it] |

## Action Items
| Task | Owner | Due | Priority |
|------|-------|-----|----------|
| [Specific task] | [Person] | [Date] | [H/M/L] |

## Commitments Made
- [Person] committed to [action] by [date]

## Discussion Summary
[2-3 paragraph narrative of topics covered]

## Open Questions
- [Unanswered question] - Follow up with [Person]

## Claims to Verify
- [Factual claim made] - needs verification
```

---

## Extraction Patterns

### Action Items
Look for phrases like:
- "I will...", "I'll..."
- "Let's...", "We should..."
- "We need to...", "Need to..."
- "Can you...", "Could you..."
- "Action item:", "TODO:"
- "[Name] will...", "[Name] to..."

### Decisions
Look for phrases like:
- "We decided...", "Decision:"
- "Let's go with...", "Going with..."
- "The decision is...", "Agreed:"
- "We're going to...", "Plan is to..."
- "Final answer:", "Conclusion:"

### Commitments
Look for phrases like:
- "I'll have it by...", "By [date]..."
- "I commit to...", "I promise..."
- "You can count on...", "I guarantee..."
- "I'll make sure...", "I'll ensure..."

### Open Questions
Look for phrases like:
- "What about...", "How do we..."
- "Need to figure out...", "TBD:"
- "Open question:", "Parking lot:"
- "Let's discuss later...", "Follow up on..."

### Claims to Verify
Look for:
- Statistics or numbers cited
- "I heard that...", "Apparently..."
- "According to...", "They said..."
- Competitive intelligence claims
- Market data assertions

---

## Voice Response

When delivering via voice, use this condensed format:

> "Meeting summary: [30-second overview]. There are [N] action items, the main one being [top priority]. Key decision was [most important]. [Person] committed to [commitment]. One thing to follow up on: [open question]."

---

## Processing Steps

1. **Parse the transcript**
   - Identify speakers if labeled
   - Break into logical sections
   - Note timestamps if available

2. **Extract structured data**
   - Pull out action items with owners
   - Identify decisions with context
   - Find commitments and deadlines
   - Note open questions

3. **Generate summary**
   - Write key takeaways (top 3 points)
   - Create narrative discussion summary
   - Flag claims that need verification

4. **Format output**
   - Use markdown template above
   - Tables for structured data
   - Bullet lists for quick scanning

5. **Offer to save**
   - "Should I save these notes to Notion?"
   - If yes, create Note with category "Note"
   - Link to relevant Project if mentioned

---

## Notion Integration

When saving to Notion:

```python
# Create a Note in the Notes database
{
    "Name": "Meeting: [Topic] - [Date]",
    "Category": "Note",
    "Project": [linked if mentioned],
    "Content": [full markdown template]
}
```

---

## Quality Checks

Before delivering meeting notes:
- [ ] All action items have owners
- [ ] Decisions have clear context
- [ ] Commitments have dates
- [ ] No speaker confusion
- [ ] Claims flagged appropriately
- [ ] Key takeaways capture essence

## Edge Cases

| Situation | Handling |
|-----------|----------|
| No clear action items | Note "No explicit action items identified" |
| Unknown speakers | Use "Speaker 1", "Speaker 2" or "Participant" |
| Informal chat | Focus on decisions/commitments, skip structure |
| Technical discussion | Include code/technical terms accurately |
| Multiple topics | Create sections for each topic |

---

## Example

**Input**:
> "Okay so we talked about the Q4 launch. Sarah said she'll have the marketing plan ready by Friday. We decided to go with the blue design. John mentioned their competitor raised $50M but I'm not sure that's right. We still need to figure out the pricing strategy. Let's meet again next Tuesday."

**Output**:

# Meeting: Q4 Launch Discussion

**Date**: [today] | **Duration**: ~5 min
**Attendees**: Sarah, John
**Next Meeting**: Tuesday

## Key Takeaways
1. Q4 launch planning is underway
2. Design decision finalized (blue)
3. Pricing strategy still needs work

## Decisions Made
| Decision | Context | Owner |
|----------|---------|-------|
| Go with blue design | Design selection for Q4 launch | - |

## Action Items
| Task | Owner | Due | Priority |
|------|-------|-----|----------|
| Complete marketing plan | Sarah | Friday | H |
| Define pricing strategy | TBD | TBD | H |

## Commitments Made
- Sarah committed to marketing plan by Friday

## Discussion Summary
Team discussed Q4 launch preparations. The main design decision was made, selecting the blue option. Marketing planning is in progress with Sarah leading. Pricing strategy identified as an open area requiring further discussion.

## Open Questions
- Pricing strategy - needs full team discussion

## Claims to Verify
- Competitor raised $50M - John mentioned, needs verification
