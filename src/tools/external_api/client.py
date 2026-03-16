"""HTTP client helpers for the external weather API tool."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib import parse, request


try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None


class UrllibResponse:
    def __init__(self, status_code: int, payload: Any) -> None:
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> Any:
        return self._payload


class UrllibRequester:
    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0,
    ) -> UrllibResponse:
        query = parse.urlencode(params or {}, doseq=True)
        full_url = url if not query else f"{url}?{query}"
        with request.urlopen(full_url, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return UrllibResponse(response.status, json.loads(payload))


def build_requester(requester: Any = None) -> Any:
    return requester or requests or UrllibRequester()
