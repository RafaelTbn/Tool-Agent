"""External API simulation tool."""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from src.services.retry_service import RetryService
from src.services.timeout_service import TimeoutService

LoggerFn = Callable[[str, Dict[str, Any]], None]


class ExternalAPITool:
    """Simulates an external API call with delay/failure/timeout handling."""

    def __init__(
        self,
        retry_service: Optional[RetryService] = None,
        timeout_service: Optional[TimeoutService] = None,
        logger: Optional[LoggerFn] = None,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self._retry = retry_service or RetryService()
        self._timeout = timeout_service or TimeoutService()
        self._logger = logger
        self._sleep = sleeper

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._normalize_query(params)
        delay = float(params.get("simulate_delay_seconds", 0.0))
        simulate_failure = bool(params.get("simulate_failure", False))
        timeout_seconds = float(params.get("timeout_seconds", 1.0))
        max_retries = int(params.get("max_retries", 2))

        def operation() -> Dict[str, Any]:
            if delay > 0:
                self._sleep(delay)
            if simulate_failure:
                raise ConnectionError("Simulated external API failure.")
            data = {
                "current_load_percentage": 72,
                "active_incidents": 1,
                "system_health": "Operational",
                "maintenance_mode": False,
                "last_updated": "2026-02-18T07:45:00Z",
            }
            return {
                "status": "ok",
                "message": (
                    f"System load is {data['current_load_percentage']}% "
                    f"with health {data['system_health']}."
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
        except Exception as exc:  # noqa: BLE001 - intentional safe fallback.
            return {
                "status": "fallback",
                "message": "External system unavailable. Please retry later.",
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
