"""Structured logger used by the tool-enabled agent."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class AgentLogger:
    """Small wrapper that emits structured log entries and keeps history."""

    name: str = "tool_agent"
    file_path: str = "logs/agent_history.jsonl"
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
        self._log_path = Path(self.file_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, payload: Dict[str, Any]) -> None:
        entry = {"event": event, "payload": payload}
        self.entries.append(entry)
        serialized = json.dumps(entry, ensure_ascii=True, sort_keys=True)
        self._logger.info(serialized)
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(serialized + "\n")

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.entries)

    def get_log_file_path(self) -> str:
        return str(self._log_path)
