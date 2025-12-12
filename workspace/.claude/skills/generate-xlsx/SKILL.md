---
name: generate-xlsx
description: Create Excel spreadsheets programmatically
triggers:
  - create spreadsheet
  - generate excel
  - make xlsx
  - create workbook
  - excel file
  - data to excel
---

# Excel Spreadsheet Generation Skill

Create professional Excel spreadsheets programmatically using openpyxl.

## When to Activate

- "Create a spreadsheet for..."
- "Generate an Excel file with..."
- "Make a budget spreadsheet"
- "Create a data tracker"
- "Export this data to Excel"

## Capabilities

### Workbook Features
- Multiple worksheets
- Named ranges
- Data validation
- Formulas
- Cell formatting
- Conditional formatting
- Charts
- Filters
- Freeze panes

### Data Types
- Text
- Numbers
- Dates
- Currency
- Percentages
- Formulas
- Hyperlinks

### Styling
- Cell colors
- Borders
- Fonts
- Alignment
- Number formats
- Column widths
- Row heights

## Implementation

### Basic Spreadsheet

```python
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference

def create_spreadsheet(title: str, sheets: list[dict]) -> str:
    """Create an Excel spreadsheet.

    Args:
        title: Workbook title (filename)
        sheets: List of sheet definitions

    Returns:
        Path to generated .xlsx file
    """
    wb = Workbook()

    # Remove default sheet
    wb.remove(wb.active)

    for sheet_def in sheets:
        add_worksheet(wb, sheet_def)

    # Save
    filename = f"workspace/files/{title.lower().replace(' ', '_')}.xlsx"
    wb.save(filename)
    return filename
```

### Sheet Definition Format

```python
sheets = [
    {
        "name": "Summary",
        "headers": ["Category", "Q1", "Q2", "Q3", "Q4", "Total"],
        "data": [
            ["Revenue", 10000, 12000, 11000, 15000, "=SUM(B2:E2)"],
            ["Expenses", 8000, 9000, 8500, 10000, "=SUM(B3:E3)"],
            ["Profit", "=B2-B3", "=C2-C3", "=D2-D3", "=E2-E3", "=SUM(B4:E4)"]
        ],
        "formatting": {
            "header_style": "bold_blue",
            "currency_columns": ["B", "C", "D", "E", "F"],
            "freeze_panes": "A2",
            "column_widths": {"A": 15, "B": 12, "C": 12, "D": 12, "E": 12, "F": 12}
        }
    },
    {
        "name": "Details",
        "headers": ["Date", "Description", "Amount", "Category"],
        "data": [
            ["2025-01-15", "Client payment", 5000, "Revenue"],
            ["2025-01-16", "Office supplies", -200, "Expenses"]
        ],
        "formatting": {
            "date_columns": ["A"],
            "currency_columns": ["C"],
            "auto_filter": True
        }
    }
]
```

### Add Worksheet

```python
def add_worksheet(wb, sheet_def: dict):
    """Add a worksheet to the workbook."""
    ws = wb.create_sheet(title=sheet_def["name"])

    # Styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    # Headers
    for col, header in enumerate(sheet_def["headers"], 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center')
        cell.border = border

    # Data
    for row_idx, row_data in enumerate(sheet_def["data"], 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.border = border

    # Formatting
    fmt = sheet_def.get("formatting", {})

    # Column widths
    for col, width in fmt.get("column_widths", {}).items():
        ws.column_dimensions[col].width = width

    # Freeze panes
    if "freeze_panes" in fmt:
        ws.freeze_panes = fmt["freeze_panes"]

    # Auto filter
    if fmt.get("auto_filter"):
        ws.auto_filter.ref = ws.dimensions

    # Number formats
    for col in fmt.get("currency_columns", []):
        for row in range(2, ws.max_row + 1):
            ws[f"{col}{row}"].number_format = '$#,##0.00'

    for col in fmt.get("date_columns", []):
        for row in range(2, ws.max_row + 1):
            ws[f"{col}{row}"].number_format = 'YYYY-MM-DD'
```

### Add Chart

```python
def add_chart(ws, chart_def: dict):
    """Add a chart to the worksheet."""
    chart = BarChart()
    chart.type = chart_def.get("type", "col")
    chart.title = chart_def.get("title", "Chart")

    # Data range
    data = Reference(
        ws,
        min_col=chart_def["data_col"],
        min_row=chart_def["data_start_row"],
        max_row=chart_def["data_end_row"]
    )

    # Categories
    categories = Reference(
        ws,
        min_col=chart_def["category_col"],
        min_row=chart_def["data_start_row"],
        max_row=chart_def["data_end_row"]
    )

    chart.add_data(data)
    chart.set_categories(categories)

    # Position
    ws.add_chart(chart, chart_def.get("position", "H2"))
```

### Spreadsheet Templates

```python
def create_budget_template() -> list[dict]:
    """Generate sheets for a budget spreadsheet."""
    return [
        {
            "name": "Monthly Budget",
            "headers": ["Category", "Budgeted", "Actual", "Difference"],
            "data": [
                ["Income", "", "", "=B2-C2"],
                ["Housing", "", "", "=B3-C3"],
                ["Transportation", "", "", "=B4-C4"],
                ["Food", "", "", "=B5-C5"],
                ["Utilities", "", "", "=B6-C6"],
                ["Other", "", "", "=B7-C7"],
                ["Total", "=SUM(B2:B7)", "=SUM(C2:C7)", "=B8-C8"]
            ],
            "formatting": {
                "header_style": "bold_blue",
                "currency_columns": ["B", "C", "D"],
                "freeze_panes": "A2"
            }
        },
        {
            "name": "Transactions",
            "headers": ["Date", "Description", "Category", "Amount"],
            "data": [],
            "formatting": {
                "date_columns": ["A"],
                "currency_columns": ["D"],
                "auto_filter": True
            }
        }
    ]

def create_tracker_template(columns: list[str]) -> list[dict]:
    """Generate sheets for a generic tracker."""
    return [
        {
            "name": "Data",
            "headers": ["ID", "Date", "Status"] + columns,
            "data": [],
            "formatting": {
                "date_columns": ["B"],
                "auto_filter": True,
                "freeze_panes": "A2"
            }
        },
        {
            "name": "Summary",
            "headers": ["Status", "Count"],
            "data": [],
            "formatting": {
                "header_style": "bold_blue"
            }
        }
    ]
```

## Workflow

### From Request

1. User: "Create a budget spreadsheet for Q1"
2. Determine spreadsheet type (budget)
3. Apply template
4. Customize for Q1
5. Save and return file path

### From Data

1. User provides data (JSON, CSV, or list)
2. Parse and structure
3. Determine appropriate formatting
4. Generate spreadsheet
5. Return file path

### From Template

1. User requests specific template
2. Apply template structure
3. Optionally pre-fill data
4. Return file path

## Response Format

### Voice (Brief)
> "I've created a budget spreadsheet with a monthly budget sheet and a transactions tracker. The file is saved to your workspace. Would you like me to pre-fill any categories?"

### Text (Detailed)
```markdown
## Spreadsheet Created

**File**: `workspace/files/q1_budget.xlsx`
**Sheets**: 2

### Sheet 1: Monthly Budget
| Column | Purpose |
|--------|---------|
| Category | Expense category |
| Budgeted | Planned amount |
| Actual | Spent amount |
| Difference | Auto-calculated |

Includes formulas for totals.

### Sheet 2: Transactions
| Column | Purpose |
|--------|---------|
| Date | Transaction date |
| Description | What it was |
| Category | Links to budget |
| Amount | Transaction amount |

Has auto-filter enabled.

### Download
- Local: `workspace/files/q1_budget.xlsx`
- [Download via S3](presigned-url)
```

## Common Templates

### Budget
- Monthly budget with categories
- Transaction log
- Summary with totals

### Project Tracker
- Task list with status
- Timeline/milestones
- Resource allocation

### Invoice
- Client details
- Line items
- Totals with tax
- Payment terms

### Data Analysis
- Raw data sheet
- Pivot summary
- Charts
- Dashboard

### Time Tracking
- Weekly hours
- Project breakdown
- Billable summary

## Error Handling

### Missing Dependencies
> "openpyxl is not installed. I can create the spreadsheet once the dependency is added."

### Invalid Data
> "Some of the data values couldn't be converted. I've marked those cells and included them as text."

### Formula Errors
> "There's a circular reference in the formulas. I've broken the cycle by making cell X a static value."

## MCP Servers

None required - uses openpyxl library directly.

## Dependencies

- `openpyxl>=3.1.0`

## Best Practices

1. **Clear headers**: Descriptive column names
2. **Data validation**: Use dropdowns where appropriate
3. **Formulas**: Document complex formulas
4. **Formatting**: Use consistent number formats
5. **Protection**: Lock formula cells if needed
6. **Named ranges**: For complex references
