"""CLI entrypoint for the tool-enabled agent."""

from __future__ import annotations

import json
import sys
from typing import Optional

from src.agent import AgentDependencies, ToolEnabledAgent
from src.logging import AgentLogger
from src.services import RetryService, TimeoutService
from src.tools import ExternalAPITool, GuardrailTool, StructuredDataTool, ToolRegistry


def build_agent() -> ToolEnabledAgent:
    """Build fully wired agent with tools, services, and logging."""
    logger = AgentLogger()
    retry_service = RetryService()
    timeout_service = TimeoutService()

    structured_tool = StructuredDataTool()
    external_tool = ExternalAPITool(
        retry_service=retry_service,
        timeout_service=timeout_service,
        logger=logger.log,
    )
    guardrail_tool = GuardrailTool()

    registry = ToolRegistry()
    registry.register("structured_data_tool", structured_tool.run)
    registry.register("external_api_tool", external_tool.run)
    registry.register("guardrail_tool", guardrail_tool.run)

    dependencies = AgentDependencies(
        structured_data_tool=registry.get("structured_data_tool"),
        external_api_tool=registry.get("external_api_tool"),
        guardrail_tool=registry.get("guardrail_tool"),
        logger=logger.log,
    )
    return ToolEnabledAgent(dependencies=dependencies)


def run(query: str) -> dict:
    """Run one query and return structured response."""
    agent = build_agent()
    return agent.handle_query(query=query)


def _query_from_cli(args: list[str]) -> Optional[str]:
    if args:
        return " ".join(args).strip()

    try:
        value = input("Enter query: ").strip()
        return value or None
    except EOFError:
        return None


if __name__ == "__main__":
    query = _query_from_cli(sys.argv[1:])
    if not query:
        print(json.dumps({"status": "error", "message": "No query provided."}))
        raise SystemExit(1)

    result = run(query)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
