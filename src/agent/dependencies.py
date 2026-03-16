"""Dependency types for the tool-enabled agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

LoggerFn = Callable[[str, Dict[str, Any]], None]
ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]
ContextualAnswerFn = Callable[[str, Dict[str, Any]], str]


@dataclass
class AgentDependencies:
    """Injected dependencies for execution and easier testing."""

    structured_data_tool: ToolFn
    external_api_tool: ToolFn
    guardrail_tool: ToolFn
    fallback_lookup_tool: Optional[ToolFn] = None
    contextual_answer: Optional[ContextualAnswerFn] = None
    logger: Optional[LoggerFn] = None
