---
name: browser-automation
description: Automate personal account management via Playwright
triggers:
  - login to
  - check my account
  - automate browser
  - check subscription
  - manage settings
  - buy
  - cancel subscription
  - web automation
---

# Browser Automation Skill

Automate personal account management and web tasks using Playwright.

## When to Activate

- "Login to my AWS console"
- "Check my subscription status on X"
- "Cancel my Netflix subscription"
- "Update my settings on..."
- "Buy X from Amazon"
- "Create an API key on..."

## Capabilities

### Account Management
- Login to services
- Navigate settings pages
- Update preferences
- Manage subscriptions

### Form Automation
- Fill out forms
- Submit applications
- Complete checkouts

### Data Extraction
- Read account status
- Extract billing info
- Get subscription details

## MCP Server

Uses `playwright` MCP server for browser automation.

## Operations

### Navigate to URL
```
Tool: browser_navigate
Params:
  url: "https://example.com/login"
```

### Take Snapshot
```
Tool: browser_snapshot
# Returns accessibility tree for current page
```

### Click Element
```
Tool: browser_click
Params:
  element: "Login button"
  ref: "button[ref='login']"
```

### Fill Form
```
Tool: browser_fill_form
Params:
  fields:
    - name: "Email"
      type: "textbox"
      ref: "input[name='email']"
      value: "user@example.com"
```

### Type Text
```
Tool: browser_type
Params:
  element: "Search box"
  ref: "input[type='search']"
  text: "search query"
```

## Workflow Example

### Check Subscription Status

1. **Navigate to service**
   ```
   browser_navigate(url="https://service.com/account")
   ```

2. **Take snapshot to see page**
   ```
   browser_snapshot()
   ```

3. **Click account/settings link**
   ```
   browser_click(element="Account Settings", ref="...")
   ```

4. **Find subscription info**
   ```
   browser_snapshot()
   # Read subscription status from page
   ```

5. **Report back**
   > "Your Netflix subscription is active. Next billing date is January 15th for $15.99."

## Approval Requirements

**ALWAYS require approval for:**
- Financial transactions (purchases)
- Canceling subscriptions
- Changing payment methods
- Deleting accounts
- Changing passwords

**Can do without approval:**
- Viewing account status
- Reading settings
- Navigating public pages
- Taking screenshots

## Security Guidelines

1. **Never store credentials** in code or logs
2. **Never screenshot** sensitive data like passwords
3. **Ask for credentials** when needed, don't assume
4. **Use 2FA** where available
5. **Clear sessions** after sensitive operations

## Response Format

### Voice (Brief)
> "I've checked your AWS console. Your current month-to-date spend is $42.50, and you have 3 running EC2 instances. Want me to show you more details?"

### Text (Detailed)
```markdown
## AWS Account Status

**Account ID**: 123456789
**Region**: ap-southeast-2

### Running Resources
- EC2 Instances: 3
- S3 Buckets: 5
- RDS Databases: 1

### Current Costs
- Month-to-date: $42.50
- Forecasted: $85.00

[View in Console](https://console.aws.amazon.com)
```

## Error Handling

### Login Failed
> "I couldn't log in to [service]. The credentials might be incorrect or there might be a CAPTCHA. Would you like to try manually?"

### Element Not Found
> "I couldn't find the [element] on the page. The website layout might have changed. Let me take a screenshot so you can see what I'm seeing."

### Timeout
> "The page is taking too long to load. This might be a network issue or the site might be down."

### CAPTCHA Detected
> "There's a CAPTCHA on this page. I can't solve CAPTCHAs automatically. Would you like me to wait while you solve it?"

## Best Practices

1. **Go slowly**: Add delays between actions
2. **Verify state**: Check page loaded before acting
3. **Handle errors**: Gracefully recover from failures
4. **Be transparent**: Show what you're doing
5. **Respect ToS**: Only automate legitimate personal use

## Limitations

- Cannot solve CAPTCHAs
- Cannot bypass 2FA (will need user input)
- Some sites detect automation
- Dynamic content may be tricky
- Session may timeout
