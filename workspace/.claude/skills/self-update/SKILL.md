---
name: self-update
description: Update code, commit, push, and restart the agent
triggers:
  - update yourself
  - restart
  - deploy update
  - install dependency
  - add package
  - reload
  - apply changes
---

# Self-Update Skill

Enable the agent to update its own code, install dependencies, commit changes, and restart itself.

## When to Activate

- "Update yourself with this new skill"
- "Install the requests package"
- "Restart to apply changes"
- "Deploy the changes you made"
- "Reload your configuration"

## Capabilities

### Code Updates
- Modify files in workspace/.claude/
- Create new skills and agents
- Update configuration

### Dependency Management
- Add Python packages to pyproject.toml
- Install via uv/pip
- Update Dockerfile if needed

### Git Operations
- Stage changes
- Commit with descriptive messages
- Push to remote

### Restart
- Save current state
- Trigger appropriate restart mechanism
- Resume task after restart

## Environment Detection

The skill auto-detects the environment and uses the appropriate restart mechanism:

```python
import os

def detect_environment():
    """Detect current runtime environment."""
    if os.environ.get("AWS_EXECUTION_ENV"):
        return "ecs"
    elif os.path.exists("/.dockerenv"):
        return "docker"
    elif os.environ.get("DOCKER_COMPOSE"):
        return "docker-compose"
    return "local"
```

## Restart Mechanisms

### Local (Docker Compose)

```bash
# Save state
echo '{"task": "...", "step": 3}' > /workspace/.claude/state/pending-task.json

# Restart container
docker-compose restart aipa
```

### AWS ECS

```bash
# Save state to EFS (persists across restarts)
echo '{"task": "...", "step": 3}' > /workspace/.claude/state/pending-task.json

# Force new deployment via AWS API MCP
aws ecs update-service \
  --cluster aipa-cluster \
  --service aipa-service \
  --force-new-deployment
```

## State Persistence

### Save State Before Restart

```json
// /workspace/.claude/state/pending-task.json
{
  "task_id": "uuid",
  "description": "Creating weather skill",
  "current_step": 3,
  "total_steps": 5,
  "context": {
    "skill_name": "weather",
    "files_created": ["SKILL.md"]
  },
  "timestamp": "2024-12-12T10:00:00Z"
}
```

### Load State On Startup

```python
import json
from pathlib import Path

STATE_FILE = Path("/workspace/.claude/state/pending-task.json")

def load_pending_task():
    """Load any pending task from previous session."""
    if STATE_FILE.exists():
        task = json.loads(STATE_FILE.read_text())
        # Clear state file after loading
        STATE_FILE.unlink()
        return task
    return None

def resume_task(task):
    """Resume a pending task."""
    print(f"Resuming: {task['description']} (step {task['current_step']}/{task['total_steps']})")
    # Continue from saved step
```

## Workflow

### Adding a New Skill

1. **Create skill files**
   ```bash
   mkdir -p /workspace/.claude/skills/new-skill/
   # Write SKILL.md and any supporting files
   ```

2. **Test the skill** (if possible without restart)
   ```bash
   # Run any tests
   pytest tests/evals/test_skills/test_new_skill.py
   ```

3. **Commit changes**
   ```bash
   git add /workspace/.claude/skills/new-skill/
   git commit -m "skill: Add new-skill for X"
   ```

4. **Push to remote**
   ```bash
   git push origin main
   ```

5. **Restart if needed**
   - Only restart if skill requires new dependencies
   - Or if configuration changes need reload

### Adding a Dependency

1. **Update pyproject.toml**
   ```toml
   dependencies = [
       # existing deps...
       "new-package>=1.0.0",
   ]
   ```

2. **Update Dockerfile** (if needed)
   ```dockerfile
   # Add any system dependencies
   ```

3. **Save state**
   ```json
   {"task": "Test new-package installation", "context": {...}}
   ```

4. **Commit and push**
   ```bash
   git add pyproject.toml Dockerfile
   git commit -m "deps: Add new-package for X feature"
   git push origin main
   ```

5. **Trigger restart**
   - ECS will pull new image on deployment
   - Docker Compose: rebuild and restart

## Safety Measures

### Pre-Restart Checklist
1. All changes committed
2. Tests pass (if applicable)
3. State saved for pending tasks
4. No uncommitted work that would be lost

### Rollback Plan
- Git history allows reverting changes
- Previous container images are available
- State file includes enough context to debug

### Limits
- Max 3 restart attempts per task
- Cooldown period between restarts
- Human approval for non-trivial changes

## Response Format

### Voice (Brief)
> "I've added the weather skill. I need to restart to load the new dependencies. This will take about 30 seconds. Should I proceed?"

### Text (Detailed)
```markdown
## Self-Update Required

### Changes Made
- Created `workspace/.claude/skills/weather/SKILL.md`
- Updated `pyproject.toml` with `httpx>=0.28.0`

### Actions Needed
1. Commit changes to git
2. Push to remote
3. Restart to install new dependencies

### Estimated Downtime
~30 seconds (ECS) or ~10 seconds (local Docker)

**Proceed with restart?**
```

## MCP Servers

- `aws-api` - For ECS restart commands
- `github` - For git operations (optional)

## Error Handling

### Restart Failed
> "The restart failed. Error: [message]. I've saved my state and will try again. If this persists, you may need to manually restart the container."

### State Load Failed
> "I found a pending task but couldn't resume it: [error]. The task was: [description]. Would you like me to start over?"

### Git Push Failed
> "I couldn't push to GitHub: [error]. Changes are committed locally. Please check your network connection or GitHub access."
