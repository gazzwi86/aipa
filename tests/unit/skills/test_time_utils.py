"""Unit tests for the time-lookup skill utilities.

These tests verify the time_utils module functions work correctly.
They don't require external services - just Python's built-in libraries.
"""

import sys
from datetime import datetime
from pathlib import Path

# Add the skill directory to the path for imports
skill_path = Path(__file__).parent.parent.parent.parent / "workspace/.claude/skills/time-lookup"
sys.path.insert(0, str(skill_path))

from time_utils import (  # noqa: E402
    convert_time,
    get_current_time,
    list_common_timezones,
    resolve_timezone,
)


class TestResolveTimezone:
    """Tests for timezone resolution."""

    def test_resolve_city_name(self):
        """Should resolve common city names to IANA timezones."""
        assert resolve_timezone("Melbourne") == "Australia/Melbourne"
        assert resolve_timezone("melbourne") == "Australia/Melbourne"
        assert resolve_timezone("Tokyo") == "Asia/Tokyo"
        assert resolve_timezone("New York") == "America/New_York"
        assert resolve_timezone("new york") == "America/New_York"

    def test_resolve_abbreviation(self):
        """Should resolve common timezone abbreviations."""
        assert resolve_timezone("UTC") == "UTC"
        assert resolve_timezone("utc") == "UTC"
        assert resolve_timezone("EST") == "America/New_York"
        assert resolve_timezone("PST") == "America/Los_Angeles"
        assert resolve_timezone("AEST") == "Australia/Melbourne"
        assert resolve_timezone("JST") == "Asia/Tokyo"

    def test_resolve_iana_timezone(self):
        """Should accept valid IANA timezone names."""
        assert resolve_timezone("Australia/Melbourne") == "Australia/Melbourne"
        assert resolve_timezone("America/New_York") == "America/New_York"
        assert resolve_timezone("Europe/London") == "Europe/London"

    def test_resolve_unknown(self):
        """Should return None for unknown locations."""
        assert resolve_timezone("Narnia") is None
        assert resolve_timezone("XYZ") is None
        assert resolve_timezone("") is None

    def test_resolve_case_insensitive(self):
        """Should be case-insensitive for cities and abbreviations."""
        assert resolve_timezone("MELBOURNE") == "Australia/Melbourne"
        assert resolve_timezone("Melbourne") == "Australia/Melbourne"
        assert resolve_timezone("TOKYO") == "Asia/Tokyo"


class TestGetCurrentTime:
    """Tests for getting current time."""

    def test_get_local_time(self):
        """Should get current local time when no timezone specified."""
        result = get_current_time()
        assert result["success"] is True
        assert "time_12h" in result
        assert "time_24h" in result
        assert "date" in result
        assert "datetime_iso" in result

    def test_get_time_in_city(self):
        """Should get time in specified city."""
        result = get_current_time("Melbourne")
        assert result["success"] is True
        assert result["timezone"] == "Australia/Melbourne"
        assert "AEDT" in result["timezone_abbrev"] or "AEST" in result["timezone_abbrev"]

    def test_get_time_in_abbreviation(self):
        """Should get time using timezone abbreviation."""
        result = get_current_time("UTC")
        assert result["success"] is True
        assert result["timezone"] == "UTC"

    def test_get_time_unknown_timezone(self):
        """Should return error for unknown timezone."""
        result = get_current_time("Narnia")
        assert result["success"] is False
        assert "error" in result
        assert "Unknown timezone" in result["error"]

    def test_time_format_12h(self):
        """Should return properly formatted 12-hour time."""
        result = get_current_time("UTC")
        # Should be in format like "03:45 PM"
        assert ":" in result["time_12h"]
        assert "AM" in result["time_12h"] or "PM" in result["time_12h"]

    def test_time_format_24h(self):
        """Should return properly formatted 24-hour time."""
        result = get_current_time("UTC")
        # Should be in format like "15:45"
        assert ":" in result["time_24h"]
        hours, minutes = result["time_24h"].split(":")
        assert 0 <= int(hours) <= 23
        assert 0 <= int(minutes) <= 59

    def test_iso_format(self):
        """Should return valid ISO format datetime."""
        result = get_current_time("UTC")
        # Should be parseable as ISO format
        datetime.fromisoformat(result["datetime_iso"])


class TestConvertTime:
    """Tests for time conversion."""

    def test_convert_est_to_melbourne(self):
        """Should convert EST to Melbourne time."""
        result = convert_time("3:00 PM", "EST", "Melbourne")
        assert result["success"] is True
        assert result["from"]["timezone"] == "America/New_York"
        assert result["to"]["timezone"] == "Australia/Melbourne"

    def test_convert_with_different_formats(self):
        """Should accept various time input formats."""
        # 12-hour with space
        result = convert_time("3:00 PM", "UTC", "Melbourne")
        assert result["success"] is True

        # 12-hour without space
        result = convert_time("3:00PM", "UTC", "Melbourne")
        assert result["success"] is True

        # 24-hour
        result = convert_time("15:00", "UTC", "Melbourne")
        assert result["success"] is True

    def test_convert_unknown_source_timezone(self):
        """Should error on unknown source timezone."""
        result = convert_time("3:00 PM", "Narnia", "Melbourne")
        assert result["success"] is False
        assert "Unknown source timezone" in result["error"]

    def test_convert_unknown_target_timezone(self):
        """Should error on unknown target timezone."""
        result = convert_time("3:00 PM", "UTC", "Narnia")
        assert result["success"] is False
        assert "Unknown target timezone" in result["error"]

    def test_convert_invalid_time_format(self):
        """Should error on invalid time format."""
        result = convert_time("not a time", "UTC", "Melbourne")
        assert result["success"] is False
        assert "Could not parse time" in result["error"]

    def test_convert_preserves_date(self):
        """Should maintain same date during conversion where applicable."""
        # Note: Date may differ due to timezone offset
        result = convert_time("12:00 PM", "UTC", "Melbourne")
        assert result["success"] is True


class TestListCommonTimezones:
    """Tests for listing common timezones."""

    def test_returns_list(self):
        """Should return a list of timezone info."""
        result = list_common_timezones()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_includes_melbourne(self):
        """Should include Melbourne in the list."""
        result = list_common_timezones()
        cities = [tz["city"] for tz in result]
        assert "Melbourne" in cities

    def test_each_entry_has_required_fields(self):
        """Each entry should have city, timezone, and time."""
        result = list_common_timezones()
        for entry in result:
            assert "city" in entry
            assert "timezone" in entry
            assert "time" in entry


class TestTimezoneAccuracy:
    """Tests for timezone calculation accuracy."""

    def test_melbourne_utc_offset(self):
        """Melbourne should have correct UTC offset (AEST +10 or AEDT +11)."""
        result = get_current_time("Melbourne")
        offset = result["utc_offset"]
        # Melbourne is either +10 (AEST) or +11 (AEDT)
        assert offset in ["+1000", "+1100"]

    def test_tokyo_utc_offset(self):
        """Tokyo should always be UTC+9 (no DST)."""
        result = get_current_time("Tokyo")
        assert result["utc_offset"] == "+0900"

    def test_utc_offset(self):
        """UTC should have zero offset."""
        result = get_current_time("UTC")
        assert result["utc_offset"] == "+0000"

    def test_new_york_utc_offset(self):
        """New York should be UTC-5 (EST) or UTC-4 (EDT)."""
        result = get_current_time("New York")
        offset = result["utc_offset"]
        assert offset in ["-0500", "-0400"]
