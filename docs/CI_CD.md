# CI/CD Pipeline Documentation

This document describes the GitHub Actions CI/CD pipeline for AIPA.

## Workflows Overview

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| CI | `ci.yml` | Push/PR to main | Code quality, security, tests |
| Deploy | `deploy.yml` | Push to main | Build, push to ECR, deploy to ECS |
| PR Review | `pr-review.yml` | Pull requests | Code review comments, security findings |
| Evaluations | `evals.yml` | Manual/Daily | Agent behavior testing |

## CI Pipeline Jobs

```
ci.yml
├── codeql          # CodeQL static analysis (security)
├── lint            # ruff + mypy
├── security        # bandit + pip-audit
├── test-unit       # pytest with coverage
├── test-e2e        # Playwright browser tests
├── terraform-validate  # terraform fmt + validate
├── docker-build    # Build container image
└── ci-success      # Gate for all checks
```

## Required Secrets

### Repository Secrets

| Secret | Required For | Description |
|--------|--------------|-------------|
| `AWS_ROLE_ARN` | deploy.yml | ARN of IAM role for OIDC auth |
| `API_ENDPOINT` | deploy.yml | Deployed API URL (for health checks) |
| `CODECOV_TOKEN` | ci.yml | Optional: Codecov upload token |

### Environment Secrets

Create a `production` environment in GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `API_ENDPOINT` | Production API URL (e.g., `https://api.example.com`) |

## AWS OIDC Configuration

The pipeline uses OIDC (OpenID Connect) for secure AWS authentication without storing long-lived credentials.

### 1. Create OIDC Provider in AWS

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Create IAM Role

Create a role with trust policy for GitHub Actions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:<OWNER>/<REPO>:*"
        }
      }
    }
  ]
}
```

### 3. Attach Required Policies

The role needs permissions for:
- ECR (push images)
- ECS (deploy services)
- S3 (terraform state)
- DynamoDB (terraform locks)
- Secrets Manager (read secrets)

Example managed policies:
- `AmazonEC2ContainerRegistryPowerUser`
- `AmazonECS_FullAccess`
- Custom policy for Terraform state

### 4. Set GitHub Secret

Add the role ARN to repository secrets:
```
AWS_ROLE_ARN=arn:aws:iam::<ACCOUNT_ID>:role/github-actions-aipa
```

## Local Development Commands

### Slash Commands

| Command | Description |
|---------|-------------|
| `/lint` | Run linting and type checking |
| `/test` | Run tests with coverage |
| `/security-scan` | Run security analysis |
| `/check-all` | Run all CI checks locally |
| `/review` | Code review with static analysis |
| `/deploy` | Terraform deploy operations |

### Direct Commands

```bash
# Linting
uv run ruff check server/ tests/
uv run ruff format --check server/ tests/
uv run mypy server/

# Security
uv run bandit -r server/ -c pyproject.toml
uv run pip-audit

# Tests
uv run pytest tests/unit -v --cov=server
uv run pytest tests/e2e -v

# Terraform
cd terraform
terraform fmt -check -recursive
terraform validate
```

## Deployment Process

### Automatic (on push to main)

1. CI workflow runs all checks
2. If CI passes, deploy workflow triggers
3. Docker image built and pushed to ECR
4. Terraform plan generated
5. ECS task definition updated
6. New task deployed to ECS
7. Health check verifies deployment

### Manual Deployment

1. Go to Actions > Deploy to AWS
2. Click "Run workflow"
3. Select environment (staging/production)
4. Monitor deployment progress

## Security Scanning

### Tools Used

| Tool | Type | Purpose |
|------|------|---------|
| CodeQL | SAST | Security vulnerabilities in code |
| Bandit | SAST | Python-specific security issues |
| pip-audit | SCA | Known vulnerabilities in dependencies |
| Checkov | IaC | Terraform security misconfigurations |

### Viewing Results

- **CodeQL**: Security tab > Code scanning alerts
- **Bandit**: PR comments (via pr-review.yml)
- **pip-audit**: PR comments (via pr-review.yml)
- **Checkov**: Use `/security-scan` command locally

## Agent Evaluations

Evaluations test the deployed agent's responses:

```bash
# Run locally
uv run pytest tests/evals -m eval -v

# CI runs daily at 6 AM UTC
# Manual trigger: Actions > Agent Evaluations > Run workflow
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EVAL_API_ENDPOINT` | `http://localhost:8000` | API to test against |
| `EVAL_TIMEOUT` | `60` | Timeout per request (seconds) |
| `EVAL_MODEL` | `claude-sonnet-4-20250514` | Model identifier |

## Troubleshooting

### CI Failures

1. **Lint failures**: Run `/lint fix` locally to auto-fix
2. **Type errors**: Check mypy output, add type hints
3. **Security issues**: Review bandit/CodeQL findings
4. **Test failures**: Run failing test locally with `-v`

### Deployment Failures

1. **ECR push failed**: Check AWS_ROLE_ARN permissions
2. **Terraform failed**: Review plan output, check state
3. **ECS deploy failed**: Check CloudWatch logs
4. **Health check failed**: Verify API_ENDPOINT secret

### Common Issues

| Issue | Solution |
|-------|----------|
| OIDC auth fails | Verify trust policy and subject claim |
| Image not found | Check ECR repository exists |
| Service unhealthy | Check ECS task logs in CloudWatch |
| Terraform drift | Run `terraform plan` locally first |

## Adding New Checks

### To CI Pipeline

1. Add job to `.github/workflows/ci.yml`
2. Add to `ci-success` needs array
3. Update this documentation

### To Local Commands

1. Create command in `.claude/commands/`
2. Add tool instructions to relevant agent
3. Update `/check-all` command

## Git Hooks

### Pre-commit Hook

Install the pre-commit hook to run checks before each commit:

```bash
ln -sf ../../.claude/hooks/pre-commit.sh .git/hooks/pre-commit
```

The hook runs:
- `ruff check` on staged Python files
- `ruff format --check` on staged Python files
- `terraform fmt -check` on staged Terraform files

### Auto-commit Hook

The `.claude/hooks/git-commit.sh` automatically commits changes to `.claude/` configuration files.

## File References

| Purpose | Location |
|---------|----------|
| CI workflow | `.github/workflows/ci.yml` |
| Deploy workflow | `.github/workflows/deploy.yml` |
| PR review workflow | `.github/workflows/pr-review.yml` |
| Evals workflow | `.github/workflows/evals.yml` |
| Pre-commit hook | `.claude/hooks/pre-commit.sh` |
| Linting config | `pyproject.toml` [tool.ruff] |
| Type checking config | `pyproject.toml` [tool.mypy] |
| Security config | `pyproject.toml` [tool.bandit] |
| Test config | `pyproject.toml` [tool.pytest] |
