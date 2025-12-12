---
name: github-workflow
description: Full GitHub workflow - repos, PRs, issues, commits
triggers:
  - create repo
  - make PR
  - create pull request
  - open issue
  - check issues
  - commit changes
  - github
  - push to
  - clone repo
---

# GitHub Workflow Skill

Full GitHub workflow operations including repository management, PRs, issues, and commits.

## When to Activate

- "Create a new repo called..."
- "Open a PR for these changes"
- "Check my open issues"
- "Create an issue about..."
- "Push these changes to GitHub"
- "Clone the repo..."
- "What PRs need review?"

## Capabilities

### Repository Operations
- Create repositories (public/private)
- Clone repositories
- Fork repositories
- List user's repositories

### Pull Requests
- Create PRs with title and description
- List open PRs
- Review PR changes
- Merge PRs (with approval)
- Close PRs

### Issues
- Create issues with labels
- List open issues
- Close issues
- Comment on issues
- Assign issues

### Commits & Branches
- Create branches
- Commit changes
- Push to remote
- View commit history

## MCP Server

Uses `github` MCP server (official GitHub MCP).

## Operations

### Create Repository

```
# Via GitHub MCP
Tool: create_repository
Params:
  name: "my-new-repo"
  description: "A new repository"
  private: true
```

### Create Issue

```
# Via GitHub MCP
Tool: create_issue
Params:
  owner: "username"
  repo: "repo-name"
  title: "Bug: Something is broken"
  body: "Description of the issue..."
  labels: ["bug"]
```

### Create Pull Request

```
# Via GitHub MCP
Tool: create_pull_request
Params:
  owner: "username"
  repo: "repo-name"
  title: "feat: Add new feature"
  body: "## Summary\n- Added feature X\n\n## Test Plan\n- Tested locally"
  head: "feature-branch"
  base: "main"
```

### List Issues

```
# Via GitHub MCP
Tool: list_issues
Params:
  owner: "username"
  repo: "repo-name"
  state: "open"
```

### Git Operations (via Bash)

```bash
# Clone repo
git clone https://github.com/owner/repo.git

# Create branch
git checkout -b feature/new-feature

# Commit changes
git add .
git commit -m "feat: Add new feature"

# Push
git push -u origin feature/new-feature
```

## Response Format

### Voice (Brief)
> "Done. I've created the issue 'Fix login bug' in your aipa repo. It's issue number 42."

### Text (Detailed)
```markdown
## Created Pull Request #15

**Title:** feat: Add user authentication
**Repository:** gazzwi86/aipa
**Branch:** feature/auth → main

### Changes
- Added login endpoint
- Added session management
- Added password hashing

[View PR](https://github.com/gazzwi86/aipa/pull/15)
```

## Approval Requirements

**ALWAYS require approval for:**
- Creating public repositories
- Deleting repositories
- Force pushing
- Merging PRs to main/master

**Can do without approval:**
- Creating private repos
- Creating issues
- Creating branches
- Creating draft PRs
- Listing/reading operations

## Error Handling

### Authentication Failed
> "GitHub authentication failed. Please check that the GITHUB_PERSONAL_ACCESS_TOKEN is set correctly."

### Repository Not Found
> "I couldn't find the repository 'owner/repo'. Check the name or your access permissions."

### Rate Limited
> "GitHub API rate limit reached. Try again in a few minutes."

## Security Notes

1. Never commit sensitive data (API keys, passwords)
2. Always use branch protection on main
3. Review PR diffs before merging
4. Don't expose tokens in commit messages
5. Use `.gitignore` for sensitive files

## Example Interactions

**Create Issue:**
> User: "Create an issue in aipa about the login bug"
> Agent: Creates issue with title derived from context, asks for details if unclear

**Create PR:**
> User: "Open a PR for my current changes"
> Agent: Gets current branch, creates PR to main, generates description from commits

**Check PRs:**
> User: "What PRs need my review?"
> Agent: Lists open PRs where user is reviewer
