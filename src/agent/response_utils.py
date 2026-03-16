"""Helpers for building agent responses and contextual answers."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.services.ollama_service import OllamaService

from .dependencies import ContextualAnswerFn, LoggerFn


def build_answer(tool_output: Dict[str, Any]) -> str:
    if "message" in tool_output:
        return str(tool_output["message"])
    return str(tool_output)


def build_response(
    status: str,
    decision: str,
    message: str,
    risk: Optional[Dict[str, Any]] = None,
    debug: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    response: Dict[str, Any] = {
        "status": status,
        "decision": decision,
        "message": message,
    }
    if risk is not None:
        response["risk"] = risk
    if debug:
        response["debug"] = debug
    return response


def build_tool_context(source: str, tool_data: Any) -> Dict[str, Any]:
    if (
        isinstance(tool_data, dict)
        and any(key in tool_data for key in ("source", "sources", "record", "records"))
    ):
        return tool_data
    return {"source": source, "record": tool_data}


def extract_context_source(context: Any, default_source: str) -> str:
    if isinstance(context, dict):
        source = context.get("source")
        if isinstance(source, str) and source:
            return source
    return default_source


def generate_contextual_answer(
    query: str,
    context: Any,
    debug: Optional[Dict[str, Any]],
    source: str,
    fallback_message: str,
    tool_output: Dict[str, Any],
    contextual_answer: Optional[ContextualAnswerFn],
    logger: Optional[LoggerFn] = None,
) -> str:
    if tool_output.get("status") != "ok" or contextual_answer is None:
        return fallback_message

    if debug is not None:
        debug["llm_input"] = {
            "query": query,
            "context": context,
        }
        debug["llm_prompt"] = OllamaService.build_prompt(query, context)

    try:
        answer = contextual_answer(query, context)
        _log(
            logger,
            "contextual_answer_generated",
            {"query": query, "source": extract_context_source(context, source)},
        )
        return answer
    except Exception as exc:
        if debug is not None:
            debug["llm_error"] = str(exc)
        _log(
            logger,
            "contextual_answer_failed",
            {"query": query, "source": source, "error": str(exc)},
        )
        return fallback_message


def build_contextual_fallback(lookup_output: Dict[str, Any]) -> str:
    data = lookup_output.get("data", {})
    if "sources" in data:
        summaries = []
        for source_entry in data.get("sources", []):
            source_name = source_entry.get("source", "unknown")
            count = source_entry.get("match_count", len(source_entry.get("records", [])))
            summaries.append(f"{count} row(s) from {source_name}")
        return "Found structured data: " + ", ".join(summaries) + "."

    source = data.get("source")
    records = data.get("records", [])
    record = data.get("record", {})

    if source == "accounts" and records:
        users = ", ".join(
            f"{item.get('user_id', 'unknown')} ({item.get('name', 'unknown user')})"
            for item in records
        )
        return f"Found {len(records)} matching accounts: {users}."

    if source == "sla_lookup" and records:
        services = ", ".join(str(item.get("service_name", "unknown")) for item in records)
        return f"Found {len(records)} matching service plans: {services}."

    if source == "policies" and records:
        policies = ", ".join(str(item.get("policy_id", "unknown")) for item in records)
        return f"Found {len(records)} matching policies: {policies}."

    if source == "sla_lookup":
        return (
            f"{record.get('service_name', 'This service')} has response time "
            f"{record.get('response_time', 'unknown')} and resolution time "
            f"{record.get('resolution_time', 'unknown')}."
        )

    if source == "accounts":
        return (
            f"Account {record.get('user_id', 'unknown')} for {record.get('name', 'unknown user')} "
            f"is {record.get('status', 'unknown')} on plan {record.get('service_plan', 'unknown')}."
        )

    if source == "policies":
        return (
            f"{record.get('title', 'Policy')} is in category {record.get('category', 'unknown')} "
            f"and applies to {', '.join(record.get('role_scope', [])) or 'unknown roles'}."
        )

    if source == "structured_data_tool":
        return f"Found relevant structured data with score {data.get('score', 'unknown')}."

    if source == "system_status":
        return (
            f"System health is {record.get('system_health', 'unknown')} with "
            f"{record.get('current_load_percentage', 'unknown')}% load and "
            f"{record.get('active_incidents', 'unknown')} active incidents."
        )

    return build_answer(lookup_output)


def _log(logger: Optional[LoggerFn], event: str, payload: Dict[str, Any]) -> None:
    if logger is not None:
        logger(event, payload)
