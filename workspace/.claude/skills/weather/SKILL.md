---
name: weather
description: Get weather information using OpenWeatherMap
triggers:
  - weather in
  - forecast
  - temperature
  - will it rain
  - weather today
  - how hot
  - how cold
---

# Weather Skill

Get current weather and forecasts using OpenWeatherMap API.

## When to Activate

- "What's the weather in Melbourne?"
- "Will it rain tomorrow?"
- "What's the forecast for the week?"
- "How hot is it outside?"
- "Do I need an umbrella today?"

## Capabilities

### Current Weather
- Temperature (actual and feels-like)
- Conditions (sunny, cloudy, rain, etc.)
- Humidity
- Wind speed and direction
- Visibility

### Forecasts
- 5-day / 3-hour forecast
- Daily summaries
- Rain probability
- Temperature highs/lows

### Location Support
- City names
- Coordinates
- Geolocation from request

## Configuration

Requires `OPENWEATHERMAP_API_KEY` environment variable.

API: https://openweathermap.org/api (Free tier: 1,000 calls/day)

## Implementation

### API Endpoints

```python
import httpx

BASE_URL = "https://api.openweathermap.org/data/2.5"
API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY")

async def get_current_weather(city: str) -> dict:
    """Get current weather for a city."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/weather",
            params={
                "q": city,
                "appid": API_KEY,
                "units": "metric"
            }
        )
        return response.json()

async def get_forecast(city: str) -> dict:
    """Get 5-day forecast for a city."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/forecast",
            params={
                "q": city,
                "appid": API_KEY,
                "units": "metric"
            }
        )
        return response.json()
```

### Location Resolution

Priority order:
1. **Explicit location** in request ("weather in Tokyo")
2. **Geolocation** from request metadata (if available)
3. **Default** (Melbourne) or ask user

```python
def resolve_location(request_text: str, geo_data: dict | None) -> str:
    """Resolve location from request or geolocation."""
    # Check for explicit location in text
    location_patterns = [
        r"weather (?:in|for|at) (.+?)(?:\?|$)",
        r"forecast (?:in|for|at) (.+?)(?:\?|$)",
    ]
    for pattern in location_patterns:
        match = re.search(pattern, request_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Use geolocation if available
    if geo_data and "city" in geo_data:
        return geo_data["city"]

    # Fallback to default
    return "Melbourne,AU"
```

## Response Format

### Voice (Brief)
> "It's currently 24 degrees and sunny in Melbourne. The humidity is 45%. It should stay clear until evening."

### Text (Detailed)
```markdown
## Weather in Melbourne

**Current Conditions** (as of 2:30 PM AEDT)

| | |
|---|---|
| Temperature | 24°C (feels like 22°C) |
| Conditions | Sunny |
| Humidity | 45% |
| Wind | 15 km/h NW |
| UV Index | High (7) |

### Today's Forecast
- High: 28°C
- Low: 16°C
- Rain chance: 0%

### 5-Day Outlook
| Day | Conditions | High | Low |
|-----|------------|------|-----|
| Thu | Sunny | 28°C | 16°C |
| Fri | Partly Cloudy | 25°C | 14°C |
| Sat | Showers | 20°C | 12°C |
| Sun | Cloudy | 18°C | 11°C |
| Mon | Sunny | 22°C | 13°C |
```

## Error Handling

### City Not Found
> "I couldn't find weather data for '[city]'. Try using a larger nearby city or specify the country (e.g., 'Melbourne, AU')."

### API Key Missing
> "Weather lookups aren't configured yet. The OPENWEATHERMAP_API_KEY needs to be set."

### Rate Limited
> "I've hit the weather API limit. Try again in a few minutes."

## Quick Answers

For simple questions, provide direct answers:

- "Do I need an umbrella?" → "No, it's sunny with 0% chance of rain."
- "Is it cold?" → "It's 24°C, so fairly warm."
- "Can I go for a run?" → "Yes, it's 18°C, partly cloudy, with light wind - great running weather."

## MCP Servers

None required - uses HTTP requests directly.

## Dependencies

- `httpx` (already in project)

## Unit Conversion

Default to metric (Celsius, km/h) for Australian user.
Support conversion if requested:
- °C to °F
- km/h to mph
- mm to inches (rainfall)
