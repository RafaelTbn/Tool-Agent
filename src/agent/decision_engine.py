"""Deterministic tool-selection logic for the Tool-enabled Agent."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Decision:
    """Represents an agent routing decision."""

    action: str
    reason: str


class DecisionEngine:
    """Rule-based decision engine.

    This intentionally avoids LLM function-calling auto mode and keeps
    behavior deterministic for production simulation requirements.
    """

    _RISK_KEYWORDS = ("delete", "bypass", "drop", "shutdown", "override")
    _STRUCTURED_KEYWORDS = (
        "sla",
        "policy",
        "account status",
        "internal database",
        "service name",
        "role",
    )
    _EXTERNAL_KEYWORDS = (
        "system load",
        "external",
        "latency",
        "uptime",
        "health check",
    )

    def decide(self, query: str) -> Decision:
        """Return deterministic action based on query content."""
        normalized = self._normalize(query)

        if any(keyword in normalized for keyword in self._RISK_KEYWORDS):
            return Decision(
                action="guardrail_refuse",
                reason="Query matches risky operation keywords.",
            )

        if any(keyword in normalized for keyword in self._STRUCTURED_KEYWORDS):
            return Decision(
                action="structured_data_tool",
                reason="Query requires deterministic structured data lookup.",
            )

        if any(keyword in normalized for keyword in self._EXTERNAL_KEYWORDS):
            return Decision(
                action="external_api_tool",
                reason="Query requests external system information.",
            )

        return Decision(
            action="direct_answer",
            reason="No tool requirement detected from deterministic rules.",
        )

    @staticmethod
    def _normalize(query: str) -> str:
        return " ".join(query.strip().lower().split())
