"""Risk and guardrail evaluation tool."""

from __future__ import annotations

from typing import Any, Dict

from src.schemas.risk_schema import RiskAssessment


class GuardrailTool:
    """Evaluates response safety and refusal/escalation requirement."""

    _REFUSAL_KEYWORDS = ("delete", "bypass", "drop", "disable security", "wipe")
    _ESCALATION_KEYWORDS = ("override", "admin access", "production access")

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._to_text(params.get("query"))
        proposed = self._to_text(params.get("proposed_answer"))
        combined = f"{query} {proposed}".strip()

        if any(keyword in combined for keyword in self._REFUSAL_KEYWORDS):
            return RiskAssessment(
                status="refused",
                risk_level="high",
                reason="Unsafe request detected by guardrail policy.",
                escalation_required=True,
            ).to_dict()

        if any(keyword in combined for keyword in self._ESCALATION_KEYWORDS):
            return RiskAssessment(
                status="approved",
                risk_level="medium",
                reason="Allowed with escalation monitoring.",
                escalation_required=True,
            ).to_dict()

        return RiskAssessment(
            status="approved",
            risk_level="low",
            reason="No unsafe patterns detected.",
            escalation_required=False,
        ).to_dict()

    @staticmethod
    def _to_text(value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).lower().split())
