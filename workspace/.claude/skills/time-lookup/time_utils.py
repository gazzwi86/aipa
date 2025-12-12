"""Time lookup utilities for the time-lookup skill.

This module provides functions for getting current time and converting between timezones.
Uses Python's built-in datetime and zoneinfo modules (Python 3.9+).
"""

from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones

# Common city name to IANA timezone mappings
CITY_TO_TIMEZONE: dict[str, str] = {
    # Australia/Pacific
    "melbourne": "Australia/Melbourne",
    "sydney": "Australia/Sydney",
    "brisbane": "Australia/Brisbane",
    "perth": "Australia/Perth",
    "adelaide": "Australia/Adelaide",
    "auckland": "Pacific/Auckland",
    "wellington": "Pacific/Auckland",
    "fiji": "Pacific/Fiji",
    # Asia
    "tokyo": "Asia/Tokyo",
    "osaka": "Asia/Tokyo",
    "singapore": "Asia/Singapore",
    "hong kong": "Asia/Hong_Kong",
    "hongkong": "Asia/Hong_Kong",
    "shanghai": "Asia/Shanghai",
    "beijing": "Asia/Shanghai",
    "seoul": "Asia/Seoul",
    "mumbai": "Asia/Kolkata",
    "delhi": "Asia/Kolkata",
    "bangalore": "Asia/Kolkata",
    "dubai": "Asia/Dubai",
    "bangkok": "Asia/Bangkok",
    "jakarta": "Asia/Jakarta",
    "kuala lumpur": "Asia/Kuala_Lumpur",
    "manila": "Asia/Manila",
    "taipei": "Asia/Taipei",
    # Europe
    "london": "Europe/London",
    "paris": "Europe/Paris",
    "berlin": "Europe/Berlin",
    "amsterdam": "Europe/Amsterdam",
    "rome": "Europe/Rome",
    "madrid": "Europe/Madrid",
    "lisbon": "Europe/Lisbon",
    "dublin": "Europe/Dublin",
    "zurich": "Europe/Zurich",
    "vienna": "Europe/Vienna",
    "stockholm": "Europe/Stockholm",
    "oslo": "Europe/Oslo",
    "copenhagen": "Europe/Copenhagen",
    "helsinki": "Europe/Helsinki",
    "moscow": "Europe/Moscow",
    "istanbul": "Europe/Istanbul",
    "athens": "Europe/Athens",
    "prague": "Europe/Prague",
    "warsaw": "Europe/Warsaw",
    "budapest": "Europe/Budapest",
    # Americas
    "new york": "America/New_York",
    "nyc": "America/New_York",
    "los angeles": "America/Los_Angeles",
    "la": "America/Los_Angeles",
    "san francisco": "America/Los_Angeles",
    "chicago": "America/Chicago",
    "houston": "America/Chicago",
    "denver": "America/Denver",
    "phoenix": "America/Phoenix",
    "seattle": "America/Los_Angeles",
    "boston": "America/New_York",
    "miami": "America/New_York",
    "atlanta": "America/New_York",
    "toronto": "America/Toronto",
    "vancouver": "America/Vancouver",
    "montreal": "America/Toronto",
    "mexico city": "America/Mexico_City",
    "sao paulo": "America/Sao_Paulo",
    "rio de janeiro": "America/Sao_Paulo",
    "buenos aires": "America/Argentina/Buenos_Aires",
    "lima": "America/Lima",
    "bogota": "America/Bogota",
    "santiago": "America/Santiago",
    # Africa
    "cairo": "Africa/Cairo",
    "johannesburg": "Africa/Johannesburg",
    "lagos": "Africa/Lagos",
    "nairobi": "Africa/Nairobi",
    "casablanca": "Africa/Casablanca",
}

# Common timezone abbreviation mappings
# Note: Many abbreviations are ambiguous (e.g., IST = India, Israel, Ireland)
ABBREV_TO_TIMEZONE: dict[str, str] = {
    # UTC/GMT
    "utc": "UTC",
    "gmt": "GMT",
    # US timezones
    "est": "America/New_York",
    "edt": "America/New_York",
    "cst": "America/Chicago",
    "cdt": "America/Chicago",
    "mst": "America/Denver",
    "mdt": "America/Denver",
    "pst": "America/Los_Angeles",
    "pdt": "America/Los_Angeles",
    "akst": "America/Anchorage",
    "akdt": "America/Anchorage",
    "hst": "Pacific/Honolulu",
    # Australia
    "aest": "Australia/Melbourne",
    "aedt": "Australia/Melbourne",
    "acst": "Australia/Adelaide",
    "acdt": "Australia/Adelaide",
    "awst": "Australia/Perth",
    # New Zealand
    "nzst": "Pacific/Auckland",
    "nzdt": "Pacific/Auckland",
    # Asia
    "jst": "Asia/Tokyo",
    "kst": "Asia/Seoul",
    "cst_asia": "Asia/Shanghai",  # China Standard Time
    "hkt": "Asia/Hong_Kong",
    "sgt": "Asia/Singapore",
    "ist": "Asia/Kolkata",  # India (most common usage)
    # Europe
    "cet": "Europe/Paris",
    "cest": "Europe/Paris",
    "wet": "Europe/Lisbon",
    "west": "Europe/Lisbon",
    "eet": "Europe/Athens",
    "eest": "Europe/Athens",
    "bst": "Europe/London",  # British Summer Time
    "msk": "Europe/Moscow",
}


def resolve_timezone(location: str) -> str | None:
    """Resolve a location/timezone string to an IANA timezone name.

    Args:
        location: City name, timezone abbreviation, or IANA timezone name

    Returns:
        IANA timezone name or None if not found
    """
    location_lower = location.lower().strip()

    # Check city mappings first (most user-friendly)
    if location_lower in CITY_TO_TIMEZONE:
        return CITY_TO_TIMEZONE[location_lower]

    # Check abbreviation mappings (prefer our mappings over raw IANA)
    if location_lower in ABBREV_TO_TIMEZONE:
        return ABBREV_TO_TIMEZONE[location_lower]

    # Check if it's a full IANA timezone path (contains /)
    if "/" in location and location in available_timezones():
        return location

    # Try case-insensitive match against IANA timezones
    for tz in available_timezones():
        if tz.lower() == location_lower:
            return tz
        # Also check the city part (e.g., "Melbourne" matches "Australia/Melbourne")
        if "/" in tz and tz.split("/")[-1].lower() == location_lower:
            return tz

    return None


def get_current_time(timezone_str: str | None = None) -> dict:
    """Get the current time, optionally in a specific timezone.

    Args:
        timezone_str: Optional timezone (city, abbreviation, or IANA name)

    Returns:
        Dictionary with time information
    """
    if timezone_str:
        tz_name = resolve_timezone(timezone_str)
        if not tz_name:
            return {
                "success": False,
                "error": f"Unknown timezone: {timezone_str}",
                "suggestion": "Try a city name like 'Melbourne' or a timezone like 'Australia/Melbourne'",
            }
        tz = ZoneInfo(tz_name)
    else:
        # Use local timezone
        tz = datetime.now().astimezone().tzinfo
        tz_name = str(tz)

    now = datetime.now(tz)

    return {
        "success": True,
        "timezone": tz_name,
        "time_12h": now.strftime("%I:%M %p"),
        "time_24h": now.strftime("%H:%M"),
        "date": now.strftime("%A, %B %d, %Y"),
        "date_short": now.strftime("%Y-%m-%d"),
        "datetime_iso": now.isoformat(),
        "utc_offset": now.strftime("%z"),
        "timezone_abbrev": now.strftime("%Z"),
        "formatted": now.strftime("%I:%M %p %Z on %A, %B %d, %Y"),
        "formatted_brief": now.strftime("%I:%M %p %Z"),
    }


def convert_time(
    time_str: str,
    from_tz: str,
    to_tz: str,
    date_str: str | None = None,
) -> dict:
    """Convert a time from one timezone to another.

    Args:
        time_str: Time string (e.g., "3:00 PM", "15:00")
        from_tz: Source timezone
        to_tz: Target timezone
        date_str: Optional date (defaults to today)

    Returns:
        Dictionary with conversion results
    """
    # Resolve timezones
    from_tz_name = resolve_timezone(from_tz)
    to_tz_name = resolve_timezone(to_tz)

    if not from_tz_name:
        return {"success": False, "error": f"Unknown source timezone: {from_tz}"}
    if not to_tz_name:
        return {"success": False, "error": f"Unknown target timezone: {to_tz}"}

    # Parse time
    time_formats = [
        "%I:%M %p",  # 3:00 PM
        "%I:%M%p",  # 3:00PM
        "%I %p",  # 3 PM
        "%I%p",  # 3PM
        "%H:%M",  # 15:00
        "%H%M",  # 1500
    ]

    parsed_time = None
    for fmt in time_formats:
        try:
            parsed_time = datetime.strptime(time_str.upper(), fmt)
            break
        except ValueError:
            continue

    if not parsed_time:
        return {
            "success": False,
            "error": f"Could not parse time: {time_str}",
            "suggestion": "Try formats like '3:00 PM', '15:00', or '3pm'",
        }

    # Get date
    if date_str:
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return {"success": False, "error": f"Invalid date format: {date_str}. Use YYYY-MM-DD"}
    else:
        date = datetime.now().date()

    # Combine date and time
    dt = datetime.combine(date, parsed_time.time())

    # Apply source timezone and convert
    from_tz_obj = ZoneInfo(from_tz_name)
    to_tz_obj = ZoneInfo(to_tz_name)

    dt_from = dt.replace(tzinfo=from_tz_obj)
    dt_to = dt_from.astimezone(to_tz_obj)

    return {
        "success": True,
        "from": {
            "timezone": from_tz_name,
            "time": dt_from.strftime("%I:%M %p"),
            "datetime": dt_from.isoformat(),
        },
        "to": {
            "timezone": to_tz_name,
            "time": dt_to.strftime("%I:%M %p"),
            "datetime": dt_to.isoformat(),
        },
        "formatted": f"{time_str} {from_tz} is {dt_to.strftime('%I:%M %p')} {to_tz}",
    }


def list_common_timezones() -> list[dict]:
    """List common timezones with current times.

    Returns:
        List of timezone info dictionaries
    """
    common_cities = [
        "Melbourne",
        "Tokyo",
        "Singapore",
        "Dubai",
        "London",
        "Paris",
        "New York",
        "Los Angeles",
    ]

    result = []
    for city in common_cities:
        time_info = get_current_time(city)
        if time_info["success"]:
            result.append(
                {
                    "city": city,
                    "timezone": time_info["timezone"],
                    "time": time_info["formatted_brief"],
                }
            )

    return result


if __name__ == "__main__":
    # Quick test
    print("Current local time:")
    print(get_current_time())
    print()

    print("Time in Melbourne:")
    print(get_current_time("Melbourne"))
    print()

    print("Time in Tokyo:")
    print(get_current_time("Tokyo"))
    print()

    print("Convert 3pm EST to Melbourne:")
    print(convert_time("3:00 PM", "EST", "Melbourne"))
    print()

    print("Common timezones:")
    for tz in list_common_timezones():
        print(f"  {tz['city']}: {tz['time']}")
