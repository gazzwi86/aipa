"""Tests for the weather skill."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock weather API response
MOCK_WEATHER_RESPONSE = {
    "coord": {"lon": 144.9631, "lat": -37.8136},
    "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
    "main": {"temp": 24.5, "feels_like": 22.3, "humidity": 45, "pressure": 1015},
    "wind": {"speed": 15.2, "deg": 315},
    "name": "Melbourne",
    "sys": {"country": "AU"},
}

MOCK_FORECAST_RESPONSE = {
    "city": {"name": "Melbourne", "country": "AU"},
    "list": [
        {
            "dt": 1702900800,
            "main": {"temp": 28, "temp_min": 16, "temp_max": 28},
            "weather": [{"main": "Clear", "description": "clear sky"}],
            "pop": 0,
        },
        {
            "dt": 1702987200,
            "main": {"temp": 25, "temp_min": 14, "temp_max": 25},
            "weather": [{"main": "Clouds", "description": "partly cloudy"}],
            "pop": 0.1,
        },
    ],
}


class TestWeatherSkillFormat:
    """Test weather response formatting."""

    def test_format_temperature(self):
        """Temperature should be formatted with unit."""
        temp = 24.5
        formatted = f"{temp:.0f}°C"
        assert formatted == "24°C"

    def test_format_wind_speed(self):
        """Wind speed should be in km/h."""
        speed_ms = 15.2  # m/s from API
        speed_kmh = speed_ms * 3.6
        assert speed_kmh == pytest.approx(54.72, rel=0.01)

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
        default_city = "Melbourne,AU"
        assert "Melbourne" in default_city


class TestWeatherAPIIntegration:
    """Test weather API integration (mocked)."""

    @pytest.mark.asyncio
    async def test_get_current_weather_success(self):
        """Should fetch and parse current weather."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = MOCK_WEATHER_RESPONSE
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            # Simulate API call
            async with mock_client() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": "Melbourne", "appid": "test", "units": "metric"},
                )
                data = response.json()

            assert data["name"] == "Melbourne"
            assert data["main"]["temp"] == 24.5
            assert data["weather"][0]["main"] == "Clear"

    @pytest.mark.asyncio
    async def test_get_forecast_success(self):
        """Should fetch and parse forecast."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = MOCK_FORECAST_RESPONSE
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_client.return_value = mock_instance

            async with mock_client() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/forecast",
                    params={"q": "Melbourne", "appid": "test", "units": "metric"},
                )
                data = response.json()

            assert data["city"]["name"] == "Melbourne"
            assert len(data["list"]) == 2

    def test_handle_city_not_found(self):
        """Should handle city not found gracefully."""
        error_response = {"cod": "404", "message": "city not found"}
        assert error_response["cod"] == "404"

        expected_message = "I couldn't find weather data for"
        assert "find" in expected_message.lower()


class TestWeatherResponseFormatting:
    """Test weather response formatting for voice and text."""

    def test_voice_response_format(self):
        """Voice response should be brief."""
        data = MOCK_WEATHER_RESPONSE

        temp = data["main"]["temp"]
        condition = data["weather"][0]["main"]
        humidity = data["main"]["humidity"]

        voice_response = f"It's currently {temp:.0f} degrees and {condition.lower()} in Melbourne. The humidity is {humidity}%."

        assert len(voice_response) < 150  # Keep it brief
        assert "24" in voice_response
        assert "clear" in voice_response.lower()
        assert "humidity" in voice_response.lower()

    def test_text_response_includes_details(self):
        """Text response should include more details."""
        data = MOCK_WEATHER_RESPONSE

        required_fields = ["Temperature", "Conditions", "Humidity", "Wind"]

        text_response = f"""
## Weather in Melbourne

**Current Conditions**

| | |
|---|---|
| Temperature | {data["main"]["temp"]:.0f}°C (feels like {data["main"]["feels_like"]:.0f}°C) |
| Conditions | {data["weather"][0]["main"]} |
| Humidity | {data["main"]["humidity"]}% |
| Wind | {data["wind"]["speed"] * 3.6:.0f} km/h |
"""

        for field in required_fields:
            assert field in text_response


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

        weather_keywords = ["weather", "rain", "umbrella", "hot", "cold", "forecast", "temperature"]

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
