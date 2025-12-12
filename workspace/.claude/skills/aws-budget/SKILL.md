---
name: aws-budget
description: Check AWS spending and costs via Cost Explorer
triggers:
  - AWS spend
  - AWS costs
  - cloud costs
  - budget
  - how much am I spending
  - AWS bill
  - monthly costs
---

# AWS Budget Skill

Check AWS spending, costs, and budget status using the AWS Cost Explorer and Budgets APIs.

## When to Activate

- "How much have I spent on AWS this month?"
- "What's my AWS bill looking like?"
- "Show me my AWS costs"
- "Am I over budget on AWS?"
- "What's my cloud spend this month?"
- "Break down my AWS costs by service"

## Capabilities

### Current Month Spend
Get the total spend for the current billing period.

### Cost Breakdown
Break down costs by:
- Service (EC2, S3, Lambda, etc.)
- Linked account (for organizations)
- Region
- Usage type

### Budget Status
Check configured AWS Budgets:
- Current vs budgeted amount
- Forecasted end-of-month spend
- Alert thresholds

### Historical Comparison
Compare current spend to previous periods.

## MCP Server

Uses `aws-api` MCP server for AWS CLI commands.

## Commands

### Get Current Month Costs

```bash
# Total costs this month
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost
```

### Get Costs by Service

```bash
# Break down by service
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

### Get Budget Status

```bash
# List all budgets
aws budgets describe-budgets --account-id ACCOUNT_ID

# Get specific budget
aws budgets describe-budget \
  --account-id ACCOUNT_ID \
  --budget-name "Monthly Budget"
```

### Get Forecasted Spend

```bash
# Forecast for rest of month
aws ce get-cost-forecast \
  --time-period Start=$(date -u +%Y-%m-%d),End=$(date -u +%Y-%m-01 -d "+1 month") \
  --metric UNBLENDED_COST \
  --granularity MONTHLY
```

## Response Format

### Voice (Brief)
> "Your AWS spend this month is $42.50. That's $8 more than last month. Your main costs are EC2 at $25 and S3 at $10."

### Text (Detailed)
```markdown
## AWS Costs - December 2024

**Month-to-Date Spend:** $42.50 USD
**Forecasted End-of-Month:** $85.00 USD

### By Service
| Service | Cost |
|---------|------|
| EC2 | $25.00 |
| S3 | $10.00 |
| RDS | $5.00 |
| Other | $2.50 |

### Budget Status
- Monthly Budget: $100.00
- Current: 42.5% used
- Status: On track
```

## Error Handling

### Access Denied
> "I don't have permission to access AWS Cost Explorer. You may need to enable Cost Explorer in your AWS account or check IAM permissions."

### No Data
> "No cost data available for this period. If this is a new account, it may take up to 24 hours for costs to appear."

### API Error
> "I couldn't retrieve AWS costs: [error message]. Try again in a few minutes."

## Required IAM Permissions

The AWS credentials need these permissions:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetCostForecast",
        "ce:GetDimensionValues",
        "budgets:ViewBudget",
        "budgets:DescribeBudgets"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

1. **Cost Explorer must be enabled** - Not enabled by default on new accounts
2. **Data delay** - Cost data can be up to 24 hours delayed
3. **Currency** - All costs are in USD by default
4. **Free tier** - The skill shows actual costs; free tier usage shows as $0
5. **Organizations** - For multi-account setups, ensure management account access

## Example Interactions

**Simple Query:**
> User: "How much have I spent on AWS?"
> Agent: Uses `aws ce get-cost-and-usage` to get current month total

**Detailed Breakdown:**
> User: "Break down my AWS costs by service"
> Agent: Uses `aws ce get-cost-and-usage` with `--group-by SERVICE`

**Budget Check:**
> User: "Am I on track with my AWS budget?"
> Agent: Uses `aws budgets describe-budgets` and compares to spend
