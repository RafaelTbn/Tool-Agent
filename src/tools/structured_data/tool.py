"""Structured data tool entrypoint."""

from __future__ import annotations

import os
from typing import Any, Dict

from .formatter import build_match_message, error_response, group_candidates, success_response
from .matcher import match_candidates
from .retriever import collect_all_candidates, connect_live_db


class StructuredDataTool:
    """Query internal SLA/policy/account data from live PostgreSQL."""

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
            candidates = collect_all_candidates(conn, str(self._db_config["db_schema"]))
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
