"""External weather API tool orchestration."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from src.services.retry_service import RetryService
from src.services.timeout_service import TimeoutService

from .client import build_requester
from .parser import (
    FORECAST_URL,
    GEOCODE_URL,
    extract_city,
    normalize_query,
    parse_location,
    parse_weather,
)

LoggerFn = Callable[[str, Dict[str, Any]], None]


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
        self._requester = build_requester(requester)
        self._geocode_url = GEOCODE_URL
        self._forecast_url = FORECAST_URL

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = normalize_query(params)
        city = extract_city(query)
        timeout_seconds = float(params.get("timeout_seconds", 5.0))
        max_retries = int(params.get("max_retries", 2))

        def operation() -> Dict[str, Any]:
            location = self._lookup_location(city, timeout_seconds)
            data = self._fetch_weather(location, timeout_seconds)
            return {
                "status": "ok",
                "message": f"Cuaca saat ini di {data['city']}: {data['temperature_c']}C, {data['condition']}.",
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

    def _lookup_location(self, city: str, timeout_seconds: float) -> Dict[str, Any]:
        response = self._requester.get(
            self._geocode_url,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        return parse_location(response.json(), city)

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
        return parse_weather(response.json(), location)

    def _on_retry(self, attempt: int, error: Exception) -> None:
        if self._logger is not None:
            self._logger(
                "retry_attempt",
                {"attempt": attempt, "error": str(error), "tool": "external_api_tool"},
            )
