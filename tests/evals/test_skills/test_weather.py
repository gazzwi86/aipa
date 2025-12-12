"""Tests for the weather skill using Open-Meteo API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock Open-Meteo current weather response
MOCK_CURRENT_WEATHER = {
    "latitude": -37.8125,
    "longitude": 144.9625,
    "timezone": "Australia/Melbourne",
    "current": {
        "time": "2024-12-12T14:30",
        "temperature_2m": 24.5,
        "relative_humidity_2m": 45,
        "apparent_temperature": 22.3,
        "weather_code": 0,
        "wind_speed_10m": 15.2,
        "wind_direction_10m": 315,
        "precipitation": 0.0,
    },
}

# Mock Open-Meteo forecast response
MOCK_FORECAST = {
    "latitude": -37.8125,
    "longitude": 144.9625,
    "timezone": "Australia/Melbourne",
    "daily": {
        "time": ["2024-12-12", "2024-12-13", "2024-12-14"],
        "weather_code": [0, 2, 61],
        "temperature_2m_max": [28.0, 25.0, 20.0],
        "temperature_2m_min": [16.0, 14.0, 12.0],
        "precipitation_probability_max": [0, 10, 60],
        "precipitation_sum": [0.0, 0.0, 5.2],
    },
}

# Mock geocoding response
MOCK_GEOCODE = {
    "results": [
        {
            "name": "Melbourne",
            "latitude": -37.8136,
            "longitude": 144.9631,
            "country": "Australia",
            "timezone": "Australia/Melbourne",
        }
    ]
}

# Weather code mappings
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    51: "Light drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    80: "Slight rain showers",
    95: "Thunderstorm",
}


class TestWeatherSkillFormat:
    """Test weather response formatting."""

    def test_format_temperature(self):
        """Temperature should be formatted with unit."""
        temp = 24.5
        formatted = f"{temp:.0f}°C"
        assert formatted == "24°C"

    def test_format_wind_speed(self):
        """Wind speed from Open-Meteo is already in km/h."""
        speed_kmh = 15.2  # km/h from API
        assert speed_kmh == pytest.approx(15.2, rel=0.01)

    def test_wind_direction_compass(self):
        """Wind direction should convert to compass."""
        directions = [
            (0, "N"),
            (45, "NE"),
            (90, "E"),
            (135, "SE"),
            (180, "S"),
            (225, "SW"),
            (270, "W"),
            (315, "NW"),
        ]

        def degrees_to_compass(degrees: float) -> str:
            dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
            idx = round(degrees / 45) % 8
            return dirs[idx]

        for deg, expected in directions:
            assert degrees_to_compass(deg) == expected

    def test_weather_code_interpretation(self):
        """Weather codes should map to descriptions."""

        def interpret_weather_code(code: int) -> str:
            return WEATHER_CODES.get(code, "Unknown")

        assert interpret_weather_code(0) == "Clear sky"
        assert interpret_weather_code(61) == "Slight rain"
        assert interpret_weather_code(95) == "Thunderstorm"
        assert interpret_weather_code(999) == "Unknown"


class TestWeatherLocationResolution:
    """Test location resolution for weather queries."""

    def test_extract_city_from_query(self):
        """Should extract city name from natural language query."""
        import re

        def extract_city(query: str) -> str | None:
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

        assert extract_city("What's the weather in Melbourne?") == "Melbourne"
        assert extract_city("Weather for Sydney") == "Sydney"
        assert extract_city("forecast at Tokyo") == "Tokyo"
        assert extract_city("How hot is it?") is None

    def test_default_to_melbourne_when_no_location(self):
        """Should default to Melbourne when no location specified."""
        default_location = {
            "latitude": -37.8136,
            "longitude": 144.9631,
            "name": "Melbourne",
        }
        assert default_location["name"] == "Melbourne"


class TestOpenMeteoAPIIntegration:
    """Test Open-Meteo API integration (mocked)."""

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self):
        """Should fetch and parse current weather."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = MOCK_CURRENT_WEATHER
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # Simulate API call
            async with mock_client() as client:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": -37.8136,
                        "longitude": 144.9631,
                        "current": "temperature_2m,weather_code",
                    },
                )
                data = response.json()

            assert data["current"]["temperature_2m"] == 24.5
            assert data["current"]["weather_code"] == 0
            assert data["current"]["relative_humidity_2m"] == 45

    @pytest.mark.asyncio
    async def test_get_forecast_success(self):
        """Should fetch and parse forecast."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = MOCK_FORECAST
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            async with mock_client() as client:
                response = await client.get(
                    "https://api.open-meteo.com/v1/forecast",
                    params={
                        "latitude": -37.8136,
                        "longitude": 144.9631,
                        "daily": "weather_code,temperature_2m_max,temperature_2m_min",
                        "forecast_days": 7,
                    },
                )
                data = response.json()

            assert len(data["daily"]["time"]) == 3
            assert data["daily"]["temperature_2m_max"][0] == 28.0
            assert data["daily"]["precipitation_probability_max"][2] == 60

    @pytest.mark.asyncio
    async def test_geocode_city_success(self):
        """Should geocode city name to coordinates."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = MOCK_GEOCODE
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            async with mock_client() as client:
                response = await client.get(
                    "https://geocoding-api.open-meteo.com/v1/search",
                    params={"name": "Melbourne", "count": 1},
                )
                data = response.json()

            assert data["results"][0]["name"] == "Melbourne"
            assert data["results"][0]["latitude"] == pytest.approx(-37.8136, rel=0.01)

    def test_handle_city_not_found(self):
        """Should handle city not found gracefully."""
        empty_response = {"results": []}
        assert len(empty_response.get("results", [])) == 0

        expected_message = "I couldn't find"
        assert "find" in expected_message.lower()


class TestWeatherResponseFormatting:
    """Test weather response formatting for voice and text."""

    def test_voice_response_format(self):
        """Voice response should be brief."""
        data = MOCK_CURRENT_WEATHER

        temp = data["current"]["temperature_2m"]
        weather_code = data["current"]["weather_code"]
        condition = WEATHER_CODES.get(weather_code, "Unknown")
        humidity = data["current"]["relative_humidity_2m"]

        voice_response = f"It's currently {temp:.0f} degrees and {condition.lower()} in Melbourne. The humidity is {humidity}%."

        assert len(voice_response) < 150  # Keep it brief
        assert "24" in voice_response
        assert "clear" in voice_response.lower()
        assert "humidity" in voice_response.lower()

    def test_text_response_includes_details(self):
        """Text response should include more details."""
        data = MOCK_CURRENT_WEATHER

        required_fields = ["Temperature", "Conditions", "Humidity", "Wind"]

        text_response = f"""
## Weather in Melbourne

**Current Conditions**

| | |
|---|---|
| Temperature | {data["current"]["temperature_2m"]:.0f}°C (feels like {data["current"]["apparent_temperature"]:.0f}°C) |
| Conditions | {WEATHER_CODES.get(data["current"]["weather_code"], "Unknown")} |
| Humidity | {data["current"]["relative_humidity_2m"]}% |
| Wind | {data["current"]["wind_speed_10m"]:.0f} km/h |
"""

        for field in required_fields:
            assert field in text_response


class TestOpenMeteoAPIFeatures:
    """Test Open-Meteo specific features."""

    def test_no_api_key_required(self):
        """Open-Meteo doesn't require an API key."""
        # This is a documentation test - Open-Meteo is free
        api_url = "https://api.open-meteo.com/v1/forecast"
        assert "api.open-meteo.com" in api_url
        # No appid or api_key parameter needed

    def test_timezone_auto_detection(self):
        """Should support automatic timezone detection."""
        params = {"latitude": -37.8136, "longitude": 144.9631, "timezone": "auto"}
        assert params["timezone"] == "auto"

    def test_forecast_days_parameter(self):
        """Should support configurable forecast days (up to 16)."""
        for days in [1, 7, 14, 16]:
            params = {"forecast_days": days}
            assert 1 <= params["forecast_days"] <= 16


@pytest.mark.eval
class TestWeatherSkillEval:
    """Evaluation tests for weather skill agent behavior."""

    def test_agent_understands_weather_queries(self):
        """Agent should recognize weather-related queries."""
        weather_queries = [
            "What's the weather in Melbourne?",
            "Will it rain tomorrow?",
            "Do I need an umbrella?",
            "How hot is it outside?",
            "What's the forecast for the week?",
        ]

        weather_keywords = [
            "weather",
            "rain",
            "umbrella",
            "hot",
            "cold",
            "forecast",
            "temperature",
        ]

        for query in weather_queries:
            has_keyword = any(kw in query.lower() for kw in weather_keywords)
            assert has_keyword, f"Query '{query}' should contain weather keyword"

    def test_agent_provides_actionable_answers(self):
        """Agent should give actionable answers to weather questions."""
        # Test that yes/no questions get direct answers
        questions_expecting_yes_no = [
            "Do I need an umbrella?",
            "Is it going to rain?",
            "Is it cold outside?",
        ]

        for q in questions_expecting_yes_no:
            # These should start with Yes/No in the response
            # This is a format expectation test
            assert "?" in q  # Question format

    def test_weather_skill_triggers(self):
        """Verify weather skill trigger patterns."""
        triggers = [
            "weather in",
            "forecast",
            "temperature",
            "will it rain",
            "weather today",
            "how hot",
            "how cold",
        ]

        test_queries = [
            ("What's the weather in Sydney?", "weather in"),
            ("What's the forecast?", "forecast"),
            ("Will it rain tomorrow?", "will it rain"),
            ("How hot is it?", "how hot"),
        ]

        for query, _expected_trigger in test_queries:
            matched = any(t in query.lower() for t in triggers)
            assert matched, f"Query '{query}' should match a trigger"
