"""Timeout helper service."""

from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


class TimeoutService:
    """Measure operation duration and enforce timeout threshold."""

    def run_with_timeout(self, operation: Callable[[], T], timeout_seconds: float) -> T:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")

        started = time.monotonic()
        result = operation()
        elapsed = time.monotonic() - started
        if elapsed > timeout_seconds:
            raise TimeoutError(
                f"Operation timed out after {elapsed:.3f}s (limit={timeout_seconds:.3f}s)."
            )
        return result
