"""Risk schema definitions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict


@dataclass(frozen=True)
class RiskAssessment:
    """Structured risk result returned by the guardrail tool."""

    status: str
    risk_level: str
    reason: str
    escalation_required: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)
