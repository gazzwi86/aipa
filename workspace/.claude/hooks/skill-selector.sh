#!/bin/bash
# Skill selector hook - reads context and suggests relevant skills
# This hook can be called to get skill recommendations based on the current context

set -e

SKILLS_DIR="$(dirname "$(dirname "$0")")/skills"
CONTEXT="$1"

# List available skills with their triggers
echo "Available skills:"
for skill_dir in "$SKILLS_DIR"/*/; do
    if [ -f "$skill_dir/SKILL.md" ]; then
        skill_name=$(basename "$skill_dir")
        # Extract description from frontmatter
        description=$(grep -A1 "^description:" "$skill_dir/SKILL.md" 2>/dev/null | tail -1 | sed 's/description: //')
        echo "  - $skill_name: $description"
    fi
done

# If context provided, suggest matching skills
if [ -n "$CONTEXT" ]; then
    echo ""
    echo "Suggested skills for context:"
    for skill_dir in "$SKILLS_DIR"/*/; do
        if [ -f "$skill_dir/SKILL.md" ]; then
            skill_name=$(basename "$skill_dir")
            # Check if any trigger matches the context
            triggers=$(grep -A10 "^triggers:" "$skill_dir/SKILL.md" 2>/dev/null | grep "^  -" | sed 's/^  - //')
            for trigger in $triggers; do
                if echo "$CONTEXT" | grep -qi "$trigger"; then
                    echo "  - $skill_name (matched: $trigger)"
                    break
                fi
            done
        fi
    done
fi
