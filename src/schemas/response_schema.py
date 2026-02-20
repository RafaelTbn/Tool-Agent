"""Response schema definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class AgentResponse:
    """Final response emitted by the agent."""

    status: str
    decision: str
    message: str
    risk: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
