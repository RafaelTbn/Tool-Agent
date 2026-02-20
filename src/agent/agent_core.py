"""Core orchestration for the tool-enabled agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .decision_engine import Decision, DecisionEngine


LoggerFn = Callable[[str, Dict[str, Any]], None]


@dataclass
class AgentDependencies:
    """Injected dependencies for execution and easier testing."""

    structured_data_tool: Callable[[Dict[str, Any]], Dict[str, Any]]
    external_api_tool: Callable[[Dict[str, Any]], Dict[str, Any]]
    guardrail_tool: Callable[[Dict[str, Any]], Dict[str, Any]]
    logger: Optional[LoggerFn] = None


class ToolEnabledAgent:
    """Main agent implementation with deterministic decision flow."""

    def __init__(
        self,
        dependencies: AgentDependencies,
        decision_engine: Optional[DecisionEngine] = None,
    ) -> None:
        self._deps = dependencies
        self._engine = decision_engine or DecisionEngine()

    def handle_query(self, query: str) -> Dict[str, Any]:
        """Execute the full flow for a single user query."""
        if not query or not query.strip():
            return self._response(
                status="error",
                decision="invalid_input",
                message="Query must not be empty.",
            )

        decision = self._engine.decide(query)
        self._log(
            "decision_made",
            {"query": query, "action": decision.action, "reason": decision.reason},
        )

        if decision.action == "guardrail_refuse":
            refusal = self._response(
                status="refused",
                decision=decision.action,
                message="Request refused due to unsafe intent.",
            )
            self._log("refusal_decision", refusal)
            return refusal

        if decision.action == "structured_data_tool":
            tool_input = {"query": query}
            self._log("tool_input", {"tool": "structured_data_tool", "input": tool_input})
            tool_output = self._deps.structured_data_tool(tool_input)
            self._log(
                "tool_output", {"tool": "structured_data_tool", "output": tool_output}
            )
            answer = self._build_answer(tool_output)
        elif decision.action == "external_api_tool":
            tool_input = {"query": query}
            self._log("tool_input", {"tool": "external_api_tool", "input": tool_input})
            tool_output = self._deps.external_api_tool(tool_input)
            self._log("tool_output", {"tool": "external_api_tool", "output": tool_output})
            answer = self._build_answer(tool_output)
        else:
            answer = "I can help with SLA, policy, account status, and system load checks."

        risk_input = {
            "query": query,
            "decision": decision.action,
            "proposed_answer": answer,
        }
        risk = self._deps.guardrail_tool(risk_input)
        self._log("risk_evaluated", {"input": risk_input, "result": risk})

        if risk.get("status") == "refused":
            refusal = self._response(
                status="refused",
                decision=decision.action,
                message=risk.get("reason", "Guardrail refused this response."),
                risk=risk,
            )
            self._log("final_response", refusal)
            return refusal

        final = self._response(
            status="ok",
            decision=decision.action,
            message=answer,
            risk=risk,
        )
        self._log("final_response", final)
        return final

    @staticmethod
    def _build_answer(tool_output: Dict[str, Any]) -> str:
        if "message" in tool_output:
            return str(tool_output["message"])
        return str(tool_output)

    @staticmethod
    def _response(
        status: str,
        decision: str,
        message: str,
        risk: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        response: Dict[str, Any] = {
            "status": status,
            "decision": decision,
            "message": message,
        }
        if risk is not None:
            response["risk"] = risk
        return response

    def _log(self, event: str, payload: Dict[str, Any]) -> None:
        if self._deps.logger is not None:
            self._deps.logger(event, payload)
