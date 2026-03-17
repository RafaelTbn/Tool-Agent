"""Structured data tool entrypoint."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from .formatter import build_match_message, error_response, group_candidates, success_response
from .matcher import match_candidates
from .retriever import collect_candidates_by_sources, connect_live_db


class StructuredDataTool:
    """Query internal SLA/policy/account data from live PostgreSQL."""

    _SOURCE_RULES = (
        ("accounts", ("account", "user", "status", "login", "plan")),
        ("sla_lookup", ("sla", "service", "support", "response time", "resolution time", "premium")),
        ("policies", ("policy", "policies", "role", "manager", "admin", "employee", "support")),
        ("system_status", ("system status", "system load", "health", "incidents", "maintenance")),
    )

    def __init__(self) -> None:
        self._db_config = {
            "db_dsn": os.getenv("DATABASE_URL", "").strip(),
            "db_host": os.getenv("DB_HOST", "localhost").strip(),
            "db_port": int(os.getenv("DB_PORT", "5432").strip() or "5432"),
            "db_name": os.getenv("DB_NAME", "tool_agent").strip(),
            "db_user": os.getenv("DB_USER", "tool_user").strip(),
            "db_password": os.getenv("DB_PASSWORD", "tool_pass").strip(),
            "db_connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "3").strip() or "3"),
            "db_schema": os.getenv("DB_SCHEMA", "intern_task").strip(),
        }

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.search_relevant(params)

    def search_relevant(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._normalize_query(params)
        conn = self._connect_live_db()
        if conn is None:
            return error_response("Live database unavailable. Check DB config and postgres container.")

        try:
            candidates = collect_candidates_by_sources(
                conn,
                str(self._db_config["db_schema"]),
                self._select_sources(query),
                self._build_query_hints(query),
            )
        finally:
            conn.close()

        matched_candidates = match_candidates(query, candidates)
        if not matched_candidates:
            return error_response("No relevant structured data found for fallback lookup.")

        grouped = group_candidates(matched_candidates)
        return success_response(grouped, build_match_message(grouped))

    def _connect_live_db(self) -> Any | None:
        return connect_live_db(self._db_config)

    @staticmethod
    def _normalize_query(params: Dict[str, Any]) -> str:
        query = params.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("structured_data_tool requires non-empty string 'query'.")
        return " ".join(query.lower().split())

    @classmethod
    def _select_sources(cls, query: str) -> List[str]:
        matched_sources: List[str] = []
        token_set = set(re.findall(r"[a-z0-9]+", query))

        for source, keywords in cls._SOURCE_RULES:
            if any(cls._matches_keyword(query, token_set, keyword) for keyword in keywords):
                matched_sources.append(source)

        if matched_sources:
            return matched_sources

        return [source for source, _ in cls._SOURCE_RULES]

    @staticmethod
    def _matches_keyword(query: str, token_set: set[str], keyword: str) -> bool:
        if " " in keyword:
            return keyword in query
        return keyword in token_set

    @staticmethod
    def _build_query_hints(query: str) -> Dict[str, Any]:
        token_set = set(re.findall(r"[a-z0-9]+", query))
        return {
            "query": query,
            "tokens": token_set,
            "user_ids": re.findall(r"\b\d{3,}\b", query),
            "service_terms": _extract_service_terms(token_set),
            "policy_terms": _extract_policy_terms(token_set),
        }


def _extract_service_terms(tokens: set[str]) -> List[str]:
    return sorted(tokens.intersection({"premium", "basic", "enterprise", "support", "service"}))


def _extract_policy_terms(tokens: set[str]) -> List[str]:
    return sorted(tokens.intersection({"policy", "policies", "manager", "admin", "employee", "support"}))
