---
name: script-runner
description: Execute Python/bash scripts for ad-hoc data tasks
triggers:
  - run script
  - execute script
  - python script
  - bash script
  - parse csv
  - transform data
  - process file
  - calculate
  - convert file
---

# Script Runner Skill

Execute Python or bash scripts for ad-hoc data processing tasks.

## When to Activate

- "Run a script to parse this CSV"
- "Execute a Python script to..."
- "Process this data and..."
- "Calculate the sum of..."
- "Convert this file to..."
- "Parse this JSON and extract..."

## Capabilities

### Python Scripts
- Data parsing (CSV, JSON, XML)
- Data transformation and analysis
- File format conversion
- Mathematical calculations
- Text processing
- Simple automation tasks

### Bash Scripts
- File operations (with safety limits)
- Text processing (awk, sed, grep)
- Simple command pipelines

## Security Constraints

### Allowed Operations
- Read files from workspace
- Write files to workspace/files/
- Standard library imports
- Data processing libraries (if installed)

### Blocked Operations
- Network requests (no urllib, requests, httpx)
- Subprocess/os.system calls
- File operations outside workspace
- Environment variable access
- Import of blocked modules

### Limits
- **Timeout**: 30 seconds default, max 120 seconds
- **Memory**: Reasonable limits via container
- **Output**: Max 100KB captured output

## Implementation

Use the `script_executor` module for safe execution:

```python
from script_executor import run_python_script, run_bash_script

# Python script execution
result = run_python_script(
    code='''
import csv
data = list(csv.reader(open('/workspace/files/data.csv')))
print(f"Found {len(data)} rows")
''',
    timeout=30
)

# Bash script execution
result = run_bash_script(
    script='wc -l /workspace/files/*.csv',
    timeout=10
)
```

## Request Patterns

### CSV Processing
```
User: "Parse this CSV and count how many rows have value > 100 in column 'price'"

Script:
import csv
count = 0
with open('/workspace/files/data.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        if float(row['price']) > 100:
            count += 1
print(f"Found {count} rows with price > 100")
```

### JSON Transformation
```
User: "Convert this JSON to CSV"

Script:
import json
import csv
with open('/workspace/files/data.json') as f:
    data = json.load(f)
with open('/workspace/files/output.csv', 'w') as f:
    writer = csv.DictWriter(f, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
print("Converted to output.csv")
```

### Data Analysis
```
User: "Calculate the average and median of the values"

Script:
import statistics
values = [10, 20, 30, 40, 50]  # or read from file
print(f"Average: {statistics.mean(values)}")
print(f"Median: {statistics.median(values)}")
```

## Response Format

### Success
> "Script completed successfully. Found 42 rows matching your criteria. The output file has been saved to `/workspace/files/result.csv`."

### Error
> "The script failed with an error: `KeyError: 'price'`. The CSV file doesn't have a column named 'price'. The available columns are: ['item', 'cost', 'quantity']."

### Timeout
> "The script timed out after 30 seconds. This might indicate an infinite loop or very large data. Try processing smaller chunks or increasing the timeout."

## MCP Servers

None required - uses subprocess execution.

## Safety Notes

1. **Always validate input** - Check file paths are within workspace
2. **Handle errors gracefully** - Catch and report meaningful errors
3. **Clean up** - Remove temporary files after processing
4. **Preview before bulk operations** - Show sample output before large transforms
5. **Never expose sensitive data** - Don't print credentials or secrets
