"""Retry helper service."""

from __future__ import annotations

from typing import Callable, Optional, TypeVar

T = TypeVar("T")


class RetryService:
    """Execute operation with deterministic retry behavior."""

    def execute(
        self,
        operation: Callable[[], T],
        retries: int,
        on_retry: Optional[Callable[[int, Exception], None]] = None,
    ) -> T:
        """Run operation and retry up to `retries` times after failures."""
        if retries < 0:
            raise ValueError("retries must be >= 0")

        last_error: Optional[Exception] = None
        for attempt in range(1, retries + 2):
            try:
                return operation()
            except Exception as exc:  # noqa: BLE001 - re-raised at the end.
                last_error = exc
                if attempt <= retries and on_retry is not None:
                    on_retry(attempt, exc)
                if attempt > retries:
                    break

        assert last_error is not None
        raise last_error
