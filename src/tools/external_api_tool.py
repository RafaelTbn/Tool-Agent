"""External weather API tool."""

from __future__ import annotations

import json
import re
from urllib import parse, request
from typing import Any, Callable, Dict, Optional

from src.services.retry_service import RetryService
from src.services.timeout_service import TimeoutService

LoggerFn = Callable[[str, Dict[str, Any]], None]

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover - exercised via fallback requester.
    requests = None


class _UrllibResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return self._payload


class _UrllibRequester:
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: float = 5.0) -> _UrllibResponse:
        query = parse.urlencode(params or {}, doseq=True)
        full_url = url if not query else f"{url}?{query}"
        with request.urlopen(full_url, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return _UrllibResponse(response.status, json.loads(payload))


class ExternalAPITool:
    """Fetch current weather data from an external API."""

    def __init__(
        self,
        retry_service: Optional[RetryService] = None,
        timeout_service: Optional[TimeoutService] = None,
        logger: Optional[LoggerFn] = None,
        requester: Any = None,
    ) -> None:
        self._retry = retry_service or RetryService()
        self._timeout = timeout_service or TimeoutService()
        self._logger = logger
        self._requester = requester or requests or _UrllibRequester()
        self._geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        self._forecast_url = "https://api.open-meteo.com/v1/forecast"

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._normalize_query(params)
        city = self._extract_city(query)
        timeout_seconds = float(params.get("timeout_seconds", 5.0))
        max_retries = int(params.get("max_retries", 2))

        def operation() -> Dict[str, Any]:
            location = self._lookup_location(city, timeout_seconds)
            data = self._fetch_weather(location, timeout_seconds)
            return {
                "status": "ok",
                "message": (
                    f"Cuaca saat ini di {data['city']}: {data['temperature_c']}C, "
                    f"{data['condition']}."
                ),
                "data": data,
                "query": query,
            }

        try:
            return self._retry.execute(
                operation=lambda: self._timeout.run_with_timeout(operation, timeout_seconds),
                retries=max_retries,
                on_retry=self._on_retry,
            )
        except Exception as exc: 
            return {
                "status": "fallback",
                "message": f"External weather API unavailable for {city}. Please retry later.",
                "error": str(exc),
                "data": {},
            }

    def _on_retry(self, attempt: int, error: Exception) -> None:
        if self._logger is not None:
            self._logger(
                "retry_attempt",
                {"attempt": attempt, "error": str(error), "tool": "external_api_tool"},
            )

    @staticmethod
    def _normalize_query(params: Dict[str, Any]) -> str:
        query = params.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("external_api_tool requires non-empty string 'query'.")
        return " ".join(query.lower().split())

    @staticmethod
    def _extract_city(query: str) -> str:
        match = re.search(r"\b(?:di|in)\s+([a-z][a-z\s'-]+)$", query)
        if match:
            return match.group(1).strip(" ?!.").title()
        return "Jakarta"

    def _lookup_location(self, city: str, timeout_seconds: float) -> Dict[str, Any]:
        response = self._requester.get(
            self._geocode_url,
            params={
                "name": city,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
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

    def _fetch_weather(self, location: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
        response = self._requester.get(
            self._forecast_url,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": (
                    "temperature_2m,apparent_temperature,relative_humidity_2m,"
                    "weather_code,wind_speed_10m"
                ),
                "timezone": "auto",
            },
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
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
            "condition": self._describe_weather_code(weather_code),
        }

    @staticmethod
    def _describe_weather_code(code: int) -> str:
        descriptions = {
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
        return descriptions.get(code, "Unknown")
