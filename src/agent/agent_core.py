"""Core orchestration for the tool-enabled agent."""

from __future__ import annotations

from typing import Dict, Optional

from .dependencies import AgentDependencies, ToolFn
from .decision_engine import DecisionEngine
from .response_utils import (
    build_answer,
    build_contextual_fallback,
    build_response,
    build_tool_context,
    extract_context_source,
    generate_contextual_answer,
)


class ToolEnabledAgent:
    """Main agent implementation with deterministic decision flow."""

    def __init__(
        self,
        dependencies: AgentDependencies,
        decision_engine: Optional[DecisionEngine] = None,
    ) -> None:
        self._deps = dependencies
        self._engine = decision_engine or DecisionEngine()

    def handle_query(self, query: str, include_debug: bool = False) -> Dict[str, Any]:
        """Execute the full flow for a single user query."""
        if not query or not query.strip():
            return build_response(
                status="error",
                decision="invalid_input",
                message="Query must not be empty.",
            )

        decision = self._engine.decide(query)
        debug: Dict[str, Any] = {}
        self._log(
            "decision_made",
            {"query": query, "action": decision.action, "reason": decision.reason},
        )

        forced_refusal: Optional[str] = None
        if decision.action == "guardrail_refuse":
            forced_refusal = "Request refused due to unsafe intent."
            answer = forced_refusal
            self._log("refusal_decision", {"decision": decision.action, "message": answer})
        elif decision.action == "structured_data_tool":
            answer = self._execute_tool(
                query=query,
                tool_name="structured_data_tool",
                tool_fn=self._deps.structured_data_tool,
                debug=debug,
            )
        elif decision.action == "external_api_tool":
            answer = self._execute_tool(
                query=query,
                tool_name="external_api_tool",
                tool_fn=self._deps.external_api_tool,
                debug=debug,
            )
        else:
            answer = self._handle_direct_answer(query, debug)

        risk_input = {
            "query": query,
            "decision": decision.action,
            "proposed_answer": answer,
        }
        risk = self._deps.guardrail_tool(risk_input)
        self._log("risk_evaluated", {"input": risk_input, "result": risk})

        if forced_refusal is not None:
            refusal = build_response(
                status="refused",
                decision=decision.action,
                message=forced_refusal,
                risk=risk,
                debug=debug if include_debug else None,
            )
            self._log("final_response", refusal)
            return refusal

        if risk.get("status") == "refused":
            refusal = build_response(
                status="refused",
                decision=decision.action,
                message=risk.get("reason", "Guardrail refused this response."),
                risk=risk,
                debug=debug if include_debug else None,
            )
            self._log("final_response", refusal)
            return refusal

        final = build_response(
            status="ok",
            decision=decision.action,
            message=answer,
            risk=risk,
            debug=debug if include_debug else None,
        )
        self._log("final_response", final)
        return final

    def _build_tool_answer(
        self,
        query: str,
        source: str,
        tool_output: Dict[str, Any],
        debug: Optional[Dict[str, Any]] = None,
    ) -> str:
        context = build_tool_context(source, tool_output.get("data", {}))
        return generate_contextual_answer(
            query=query,
            context=context,
            debug=debug,
            source=source,
            fallback_message=build_answer(tool_output),
            tool_output=tool_output,
            contextual_answer=self._deps.contextual_answer,
            logger=self._deps.logger,
        )

    def _log(self, event: str, payload: Dict[str, Any]) -> None:
        if self._deps.logger is not None:
            self._deps.logger(event, payload)

    def _handle_direct_answer(self, query: str, debug: Optional[Dict[str, Any]] = None) -> str:
        default_answer = "I can help with SLA, policy, account status, and system load checks."
        if self._deps.fallback_lookup_tool is None:
            return default_answer

        lookup_output = self._run_tool("fallback_lookup_tool", self._deps.fallback_lookup_tool, query)

        if lookup_output.get("status") != "ok":
            return default_answer

        return generate_contextual_answer(
            query=query,
            context=lookup_output.get("data", {}),
            debug=debug,
            source=extract_context_source(lookup_output.get("data", {}), "fallback_lookup_tool"),
            fallback_message=build_contextual_fallback(lookup_output),
            tool_output=lookup_output,
            contextual_answer=self._deps.contextual_answer,
            logger=self._deps.logger,
        )

    def _execute_tool(
        self,
        query: str,
        tool_name: str,
        tool_fn: ToolFn,
        debug: Optional[Dict[str, Any]] = None,
    ) -> str:
        tool_output = self._run_tool(tool_name, tool_fn, query)
        return self._build_tool_answer(query, tool_name, tool_output, debug)

    def _run_tool(self, tool_name: str, tool_fn: ToolFn, query: str) -> Dict[str, Any]:
        tool_input = {"query": query}
        self._log("tool_input", {"tool": tool_name, "input": tool_input})
        tool_output = tool_fn(tool_input)
        self._log("tool_output", {"tool": tool_name, "output": tool_output})
        return tool_output
