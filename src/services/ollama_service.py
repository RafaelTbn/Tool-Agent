"""Small Ollama client used for contextual answer generation."""

from __future__ import annotations

import json
from typing import Any, Dict
from urllib import error, request


class OllamaService:
    """Minimal wrapper around the Ollama generate API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:3b",
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_seconds = timeout_seconds

    def answer_with_context(self, query: str, context: Dict[str, Any]) -> str:
        prompt = (
            "You answer user questions using only the provided internal data.\n"
            "If the data is insufficient, say so briefly.\n"
            "Keep the answer concise and factual.\n\n"
            f"User query: {query.strip()}\n"
            f"Structured data: {json.dumps(context, ensure_ascii=True, sort_keys=True)}"
        )

        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
            }
        ).encode("utf-8")
        http_request = request.Request(
            url=f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama request failed with status {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Ollama is unreachable at {self._base_url}.") from exc

        answer = str(response_payload.get("response", "")).strip()
        if not answer:
            raise ValueError("Ollama returned an empty response.")
        return answer
