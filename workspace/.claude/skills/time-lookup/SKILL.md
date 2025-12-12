---
name: time-lookup
description: Get current time and timezone conversions
triggers:
  - what time
  - current time
  - time in
  - timezone
  - what's the time
---

# Time Lookup Skill

Get current time, time at any location, and timezone conversions.

## When to Activate

- "What time is it?"
- "What time is it in Tokyo?"
- "Current time in UTC"
- "Convert 3pm EST to Sydney time"
- "What timezone is London in?"

## Capabilities

### Current Time
Get the current time in the local timezone or any specified timezone.

### Time at Location
Get the current time at any city or timezone:
- Major cities: "time in New York", "time in Tokyo"
- Timezone codes: "time in UTC", "time in PST"
- Country/Region: "time in Australia/Sydney"

### Timezone Conversion
Convert times between timezones:
- "Convert 3pm EST to UTC"
- "What's 9am Tokyo time in London?"

## Implementation

Use Python's built-in `datetime` and `zoneinfo` modules (Python 3.9+).

```python
from datetime import datetime
from zoneinfo import ZoneInfo

# Get current time in a timezone
def get_time_in_timezone(tz_name: str) -> str:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    return now.strftime("%I:%M %p %Z on %A, %B %d, %Y")

# Common timezone mappings
CITY_TO_TIMEZONE = {
    "sydney": "Australia/Sydney",
    "melbourne": "Australia/Melbourne",
    "tokyo": "Asia/Tokyo",
    "london": "Europe/London",
    "new york": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "singapore": "Asia/Singapore",
    "hong kong": "Asia/Hong_Kong",
    "dubai": "Asia/Dubai",
    "mumbai": "Asia/Kolkata",
    "beijing": "Asia/Shanghai",
    "moscow": "Europe/Moscow",
    "sao paulo": "America/Sao_Paulo",
    "chicago": "America/Chicago",
    "denver": "America/Denver",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "auckland": "Pacific/Auckland",
}

# Common abbreviation mappings
ABBREV_TO_TIMEZONE = {
    "utc": "UTC",
    "gmt": "GMT",
    "est": "America/New_York",
    "edt": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "aest": "Australia/Sydney",
    "aedt": "Australia/Sydney",
    "awst": "Australia/Perth",
    "nzst": "Pacific/Auckland",
    "nzdt": "Pacific/Auckland",
    "jst": "Asia/Tokyo",
    "kst": "Asia/Seoul",
    "cet": "Europe/Paris",
    "cest": "Europe/Paris",
    "bst": "Europe/London",
    "ist": "Asia/Kolkata",
}
```

## Response Format

### Voice (Brief)
> "It's 3:45 PM in Sydney, Thursday December 12th."

### Text (Detailed)
```
Current time in Sydney (Australia/Sydney):
3:45 PM AEDT on Thursday, December 12, 2024

UTC: 4:45 AM
Your local time: [if different]
```

## Error Handling

- Unknown city: "I don't recognize that city. Try using the timezone like 'America/New_York' or a well-known city."
- Invalid timezone: "That's not a valid timezone. Common formats: UTC, EST, PST, or 'Asia/Tokyo'."

## MCP Servers

None required - uses Python standard library only.

## Notes

- Always use IANA timezone database names internally (e.g., "America/New_York")
- Support common abbreviations (EST, PST, etc.) but note they can be ambiguous
- For daylight saving awareness, always use the full timezone name
