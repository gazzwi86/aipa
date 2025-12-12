---
name: weather
description: Get weather information using Open-Meteo (free, no API key)
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

Get current weather and forecasts using Open-Meteo API - completely free, no API key required.

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
- Precipitation probability

### Forecasts
- 16-day forecast
- Hourly data
- Daily summaries
- Rain probability
- Temperature highs/lows

### Location Support
- City names (via geocoding)
- Coordinates (direct)
- Geolocation from request

## Configuration

**No API key required!** Open-Meteo is free for non-commercial use.

API: https://open-meteo.com/ (Free: 10,000 requests/day)

## Implementation

### Geocoding (City Name to Coordinates)

```python
import httpx

async def geocode_city(city: str) -> dict | None:
    """Convert city name to coordinates using Open-Meteo Geocoding API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "format": "json"}
        )
        data = response.json()
        if data.get("results"):
            result = data["results"][0]
            return {
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "name": result["name"],
                "country": result.get("country", ""),
                "timezone": result.get("timezone", "auto")
            }
        return None
```

### Current Weather

```python
async def get_current_weather(latitude: float, longitude: float) -> dict:
    """Get current weather for coordinates."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,precipitation",
                "timezone": "auto"
            }
        )
        return response.json()
```

### Forecast

```python
async def get_forecast(latitude: float, longitude: float, days: int = 7) -> dict:
    """Get weather forecast for coordinates."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum",
                "timezone": "auto",
                "forecast_days": days
            }
        )
        return response.json()
```

### Weather Code Interpretation

```python
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

def interpret_weather_code(code: int) -> str:
    return WEATHER_CODES.get(code, "Unknown")
```

### Location Resolution

Priority order:
1. **Explicit location** in request ("weather in Tokyo")
2. **Geolocation** from request metadata (if available)
3. **Default** (Melbourne) or ask user

```python
import re

def extract_location_from_query(query: str) -> str | None:
    """Extract location from natural language query."""
    patterns = [
        r"weather (?:in|for|at) (.+?)(?:\?|$)",
        r"forecast (?:in|for|at) (.+?)(?:\?|$)",
        r"temperature (?:in|for|at) (.+?)(?:\?|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None

async def resolve_location(query: str, geo_data: dict | None) -> dict:
    """Resolve location from query or geolocation."""
    # Check for explicit location in text
    city = extract_location_from_query(query)
    if city:
        location = await geocode_city(city)
        if location:
            return location

    # Use geolocation if available
    if geo_data:
        if "latitude" in geo_data and "longitude" in geo_data:
            return {
                "latitude": geo_data["latitude"],
                "longitude": geo_data["longitude"],
                "name": geo_data.get("city", "Your location"),
                "timezone": geo_data.get("timezone", "auto")
            }
        if "city" in geo_data:
            location = await geocode_city(geo_data["city"])
            if location:
                return location

    # Fallback to Melbourne
    return {
        "latitude": -37.8136,
        "longitude": 144.9631,
        "name": "Melbourne",
        "country": "Australia",
        "timezone": "Australia/Melbourne"
    }
```

## Response Format

### Voice (Brief)
> "It's currently 24 degrees and sunny in Melbourne. The humidity is 45%. It should stay clear until evening."

### Text (Detailed)
```markdown
## Weather in Melbourne

**Current Conditions**

| | |
|---|---|
| Temperature | 24°C (feels like 22°C) |
| Conditions | Clear sky |
| Humidity | 45% |
| Wind | 15 km/h NW |
| Precipitation | 0 mm |

### Today's Forecast
- High: 28°C
- Low: 16°C
- Rain chance: 0%

### 7-Day Outlook
| Day | Conditions | High | Low | Rain |
|-----|------------|------|-----|------|
| Thu | Clear | 28°C | 16°C | 0% |
| Fri | Partly cloudy | 25°C | 14°C | 10% |
| Sat | Rain showers | 20°C | 12°C | 60% |
| Sun | Overcast | 18°C | 11°C | 20% |
| Mon | Clear | 22°C | 13°C | 0% |
```

## Error Handling

### City Not Found
> "I couldn't find '[city]'. Try using a larger nearby city or check the spelling."

### API Error
> "I'm having trouble getting weather data right now. Try again in a moment."

## Quick Answers

For simple questions, provide direct answers:

- "Do I need an umbrella?" → "No, it's sunny with 0% chance of rain."
- "Is it cold?" → "It's 24°C, so fairly warm."
- "Can I go for a run?" → "Yes, it's 18°C, partly cloudy, with light wind - great running weather."
- "Will it rain tomorrow?" → "There's a 60% chance of rain tomorrow with up to 5mm expected."

## MCP Servers

None required - uses HTTP requests directly.

## Dependencies

- `httpx` (already in project)

## Unit Conversion

Default to metric (Celsius, km/h) for Australian user.
Support conversion if requested:
- °C to °F: `(celsius * 9/5) + 32`
- km/h to mph: `kmh * 0.621371`
- mm to inches: `mm * 0.0393701`

## API Reference

- Forecast API: https://open-meteo.com/en/docs
- Geocoding API: https://open-meteo.com/en/docs/geocoding-api
- Weather codes: https://open-meteo.com/en/docs#weathervariables
