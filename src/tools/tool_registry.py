"""Registry for agent tools."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

ToolFn = Callable[[Dict[str, Any]], Dict[str, Any]]


class ToolRegistry:
    """Simple in-memory tool registry."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolFn] = {}

    def register(self, name: str, tool_fn: ToolFn) -> None:
        if not name.strip():
            raise ValueError("tool name must not be empty")
        self._tools[name] = tool_fn

    def get(self, name: str) -> ToolFn:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())
