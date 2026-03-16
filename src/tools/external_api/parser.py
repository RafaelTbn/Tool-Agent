"""Parsing helpers for external weather API responses."""

from __future__ import annotations

import re
from typing import Any, Dict


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

WEATHER_DESCRIPTIONS = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
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
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


def normalize_query(params: Dict[str, Any]) -> str:
    query = params.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("external_api_tool requires non-empty string 'query'.")
    return " ".join(query.lower().split())


def extract_city(query: str) -> str:
    match = re.search(r"\b(?:di|in)\s+([a-z][a-z\s'-]+)$", query)
    if match:
        return match.group(1).strip(" ?!.").title()
    return "Jakarta"


def parse_location(payload: Dict[str, Any], city: str) -> Dict[str, Any]:
    results = payload.get("results") or []
    if not results:
        raise LookupError(f"Location '{city}' not found.")

    first = results[0]
    return {
        "city": str(first.get("name", city)),
        "country": str(first.get("country", "")),
        "latitude": float(first["latitude"]),
        "longitude": float(first["longitude"]),
    }


def parse_weather(payload: Dict[str, Any], location: Dict[str, Any]) -> Dict[str, Any]:
    current = payload.get("current") or {}
    if not current:
        raise LookupError("Weather data missing from API response.")

    weather_code = int(current.get("weather_code", -1))
    return {
        "city": location["city"],
        "country": location["country"],
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "temperature_c": current.get("temperature_2m"),
        "apparent_temperature_c": current.get("apparent_temperature"),
        "humidity_percent": current.get("relative_humidity_2m"),
        "wind_speed_kph": current.get("wind_speed_10m"),
        "weather_code": weather_code,
        "condition": WEATHER_DESCRIPTIONS.get(weather_code, "Unknown"),
    }
