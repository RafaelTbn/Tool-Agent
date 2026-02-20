"""Request schema definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class AgentRequest:
    """Incoming user request for the tool-enabled agent."""

    query: str
    params: Dict[str, Any] = field(default_factory=dict)
