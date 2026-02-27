"""Structured logger used by the tool-enabled agent."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentLogger:
    """Small wrapper that emits structured log entries and keeps history."""

    name: str = "tool_agent"
    entries: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._logger = logging.getLogger(self.name)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

    def log(self, event: str, payload: Dict[str, Any]) -> None:
        entry = {"event": event, "payload": payload}
        self.entries.append(entry)
        self._logger.info(json.dumps(entry, ensure_ascii=True, sort_keys=True))
