"""Parsing helpers for external weather API responses."""

from __future__ import annotations

import re
from typing import Any, Dict, List


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
    match = re.search(r"\b(?:di|in)\s+([a-z][a-z\s,'-]+)$", query)
    raw_location = match.group(1).strip(" ?!.") if match else "jakarta"
    city_part = re.split(r",", raw_location, maxsplit=1)[0].strip()
    words = [word for word in city_part.split() if word]
    if not words:
        return "Jakarta"
    return " ".join(word.title() for word in words)


def parse_location(payload: Dict[str, Any], city: str) -> Dict[str, Any]:
    results = payload.get("results") or []
    if not results:
        raise LookupError(f"Location '{city}' not found.")

    first = _select_best_location(results, city)
    display_city = _display_city_name(first, city)
    return {
        "city": display_city,
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


def _select_best_location(results: List[Dict[str, Any]], city: str) -> Dict[str, Any]:
    normalized_city = _normalize_location_name(city)
    ranked = sorted(
        results,
        key=lambda candidate: _location_score(candidate, normalized_city),
        reverse=True,
    )
    return ranked[0]


def _location_score(
    candidate: Dict[str, Any],
    normalized_city: str,
) -> tuple[int, int, int, int, int]:
    name = _normalize_location_name(str(candidate.get("name", "")))
    admin1 = _normalize_location_name(str(candidate.get("admin1", "")))
    admin2 = _normalize_location_name(str(candidate.get("admin2", "")))
    admin3 = _normalize_location_name(str(candidate.get("admin3", "")))
    admin4 = _normalize_location_name(str(candidate.get("admin4", "")))

    exact_name = int(name == normalized_city)
    exact_admin = int(normalized_city in {admin1, admin2, admin3, admin4})
    contains_name = int(bool(normalized_city and normalized_city in name))
    feature_rank = _feature_rank(str(candidate.get("feature_code", "")))
    population = int(candidate.get("population", 0) or 0)

    return (
        exact_name,
        exact_admin,
        contains_name,
        feature_rank,
        population,
    )


def _normalize_location_name(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _display_city_name(candidate: Dict[str, Any], requested_city: str) -> str:
    requested = _normalize_location_name(requested_city)
    candidate_name = str(candidate.get("name", requested_city))
    normalized_name = _normalize_location_name(candidate_name)
    admin_values = {
        _normalize_location_name(str(candidate.get("admin1", ""))),
        _normalize_location_name(str(candidate.get("admin2", ""))),
        _normalize_location_name(str(candidate.get("admin3", ""))),
        _normalize_location_name(str(candidate.get("admin4", ""))),
    }

    if requested and (requested == normalized_name or requested in admin_values):
        return requested_city
    return candidate_name


def _feature_rank(feature_code: str) -> int:
    rankings = {
        "PPLC": 6,
        "PPLA": 5,
        "PPLA2": 4,
        "PPLA3": 3,
        "PPLA4": 2,
        "PPL": 1,
    }
    return rankings.get(feature_code.upper(), 0)
