"""Deterministic structured-data query tool backed by live PostgreSQL."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List


class StructuredDataTool:
    """Query internal SLA/policy/account data from live PostgreSQL."""

    def __init__(self) -> None:
        self._db_dsn = os.getenv("DATABASE_URL", "").strip()
        self._db_host = os.getenv("DB_HOST", "localhost").strip()
        self._db_port = int(os.getenv("DB_PORT", "5432").strip() or "5432")
        self._db_name = os.getenv("DB_NAME", "tool_agent").strip()
        self._db_user = os.getenv("DB_USER", "tool_user").strip()
        self._db_password = os.getenv("DB_PASSWORD", "tool_pass").strip()
        self._db_connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", "3").strip() or "3")
        self._db_schema = os.getenv("DB_SCHEMA", "intern_task").strip()

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._normalize_query(params)
        conn = self._connect_live_db()
        if conn is None:
            return {
                "status": "error",
                "message": "Live database unavailable. Check DB config and postgres container.",
                "data": {},
            }

        try:
            if "sla" in query:
                return self._lookup_sla_db(conn, query)
            if "policy" in query:
                return self._lookup_policy_db(conn, query)
            if "account status" in query or "account" in query:
                return self._lookup_account_db(conn, query)

            return {
                "status": "error",
                "message": "Unsupported structured query. Use SLA, policy, or account status.",
                "data": {},
            }
        finally:
            conn.close()

    def search_relevant(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find relevant structured data even when keyword routing does not match."""
        query = self._normalize_query(params)
        conn = self._connect_live_db()
        if conn is None:
            return {
                "status": "error",
                "message": "Live database unavailable. Check DB config and postgres container.",
                "data": {},
            }

        try:
            candidates: List[Dict[str, Any]] = []
            candidates.extend(self._collect_sla_candidates(conn))
            candidates.extend(self._collect_policy_candidates(conn))
            candidates.extend(self._collect_account_candidates(conn))
            candidates.extend(self._collect_system_status_candidates(conn))
        finally:
            conn.close()

        query_tokens = self._tokenize(query)
        best_candidate: Dict[str, Any] | None = None
        best_score = 0

        for candidate in candidates:
            score = self._score_candidate(query, query_tokens, candidate["match_text"])
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_candidate is None or best_score < 2:
            return {
                "status": "error",
                "message": "No relevant structured data found for fallback lookup.",
                "data": {},
            }

        return {
            "status": "ok",
            "message": f"Found fallback structured data from {best_candidate['source']}.",
            "data": {
                "source": best_candidate["source"],
                "record": best_candidate["record"],
                "score": best_score,
            },
        }

    @staticmethod
    def _normalize_query(params: Dict[str, Any]) -> str:
        query = params.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("structured_data_tool requires non-empty string 'query'.")
        return " ".join(query.lower().split())

    def _connect_live_db(self) -> Any | None:
        try:
            import psycopg  # type: ignore
        except Exception:
            return None

        try:
            if self._db_dsn:
                return psycopg.connect(self._db_dsn, connect_timeout=self._db_connect_timeout)
            return psycopg.connect(
                host=self._db_host,
                port=self._db_port,
                dbname=self._db_name,
                user=self._db_user,
                password=self._db_password,
                connect_timeout=self._db_connect_timeout,
            )
        except Exception:
            return None

    def _lookup_sla_db(self, conn: Any, query: str) -> Dict[str, Any]:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    service_name,
                    tier,
                    response_time,
                    resolution_time,
                    availability,
                    support_channels,
                    escalation_available
                FROM {self._db_schema}.sla_lookup
                """
            )
            rows = cur.fetchall()

        for row in rows:
            service_name = str(row[0])
            if service_name.lower() in query:
                record = {
                    "service_name": service_name,
                    "tier": str(row[1]),
                    "response_time": str(row[2]),
                    "resolution_time": str(row[3]),
                    "availability": str(row[4]),
                    "support_channels": list(row[5]),
                    "escalation_available": bool(row[6]),
                }
                return {
                    "status": "ok",
                    "message": (
                        f"SLA for {record['service_name']}: response {record['response_time']}, "
                        f"resolution {record['resolution_time']}."
                    ),
                    "data": record,
                }

        return {
            "status": "error",
            "message": "SLA service name not found in query.",
            "data": {},
        }

    def _lookup_policy_db(self, conn: Any, query: str) -> Dict[str, Any]:
        for role in ("employee", "manager", "admin", "support"):
            if role in query:
                role_title = role.capitalize()
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT policy_id, title, category, description, role_scope
                        FROM {self._db_schema}.policies
                        WHERE %s = ANY(role_scope)
                        ORDER BY policy_id
                        """,
                        (role_title,),
                    )
                    rows = cur.fetchall()

                matches = [
                    {
                        "policy_id": str(row[0]),
                        "title": str(row[1]),
                        "category": str(row[2]),
                        "description": str(row[3]),
                        "role_scope": list(row[4]),
                    }
                    for row in rows
                ]
                return {
                    "status": "ok",
                    "message": f"Found {len(matches)} policies for role {role_title}.",
                    "data": {"role": role_title, "policies": matches},
                }

        return {
            "status": "error",
            "message": "Policy role not found. Include employee/manager/admin/support.",
            "data": {},
        }

    def _lookup_account_db(self, conn: Any, query: str) -> Dict[str, Any]:
        matched = re.search(r"\b\d{3,}\b", query)
        if not matched:
            return {
                "status": "error",
                "message": "Account query must include numeric user id.",
                "data": {},
            }

        user_id = matched.group(0)
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT user_id, name, role, status, service_plan, last_login
                FROM {self._db_schema}.accounts
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()

        if row is None:
            return {
                "status": "error",
                "message": f"Account {user_id} not found.",
                "data": {},
            }

        account = {
            "user_id": str(row[0]),
            "name": str(row[1]),
            "role": str(row[2]),
            "status": str(row[3]),
            "service_plan": str(row[4]),
            "last_login": str(row[5]),
        }
        return {
            "status": "ok",
            "message": f"Account {user_id} status is {account['status']}.",
            "data": account,
        }

    def _collect_sla_candidates(self, conn: Any) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    service_name,
                    tier,
                    response_time,
                    resolution_time,
                    availability,
                    support_channels,
                    escalation_available
                FROM {self._db_schema}.sla_lookup
                """
            )
            rows = cur.fetchall()

        candidates = []
        for row in rows:
            record = {
                "service_name": str(row[0]),
                "tier": str(row[1]),
                "response_time": str(row[2]),
                "resolution_time": str(row[3]),
                "availability": str(row[4]),
                "support_channels": list(row[5]),
                "escalation_available": bool(row[6]),
            }
            candidates.append(
                {
                    "source": "sla_lookup",
                    "match_text": " ".join(
                        [
                            record["service_name"],
                            record["tier"],
                            record["response_time"],
                            record["resolution_time"],
                            record["availability"],
                            " ".join(record["support_channels"]),
                            "service support plan",
                        ]
                    ),
                    "record": record,
                }
            )
        return candidates

    def _collect_policy_candidates(self, conn: Any) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT p.policy_id, p.title, p.category, p.description, p.role_scope, pr.rule_text
                FROM {self._db_schema}.policies p
                LEFT JOIN {self._db_schema}.policy_rules pr
                    ON p.policy_id = pr.policy_id
                ORDER BY p.policy_id, pr.rule_order
                """
            )
            rows = cur.fetchall()

        grouped: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            policy_id = str(row[0])
            if policy_id not in grouped:
                grouped[policy_id] = {
                    "policy_id": policy_id,
                    "title": str(row[1]),
                    "category": str(row[2]),
                    "description": str(row[3]),
                    "role_scope": list(row[4]),
                    "rules": [],
                }
            if len(row) > 5 and row[5] is not None:
                grouped[policy_id]["rules"].append(str(row[5]))

        candidates = []
        for record in grouped.values():
            candidates.append(
                {
                    "source": "policies",
                    "match_text": " ".join(
                        [
                            record["policy_id"],
                            record["title"],
                            record["category"],
                            record["description"],
                            " ".join(record["role_scope"]),
                            " ".join(record["rules"]),
                        ]
                    ),
                    "record": record,
                }
            )
        return candidates

    def _collect_account_candidates(self, conn: Any) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT user_id, name, role, status, service_plan, last_login
                FROM {self._db_schema}.accounts
                """
            )
            rows = cur.fetchall()

        candidates = []
        for row in rows:
            record = {
                "user_id": str(row[0]),
                "name": str(row[1]),
                "role": str(row[2]),
                "status": str(row[3]),
                "service_plan": str(row[4]),
                "last_login": str(row[5]),
            }
            candidates.append(
                {
                    "source": "accounts",
                    "match_text": " ".join(record.values()),
                    "record": record,
                }
            )
        return candidates

    def _collect_system_status_candidates(self, conn: Any) -> List[Dict[str, Any]]:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT current_load_percentage, active_incidents, system_health, maintenance_mode, last_updated
                FROM {self._db_schema}.system_status
                WHERE id = 1
                """
            )
            row = cur.fetchone()

        if row is None:
            return []

        record = {
            "current_load_percentage": int(row[0]),
            "active_incidents": int(row[1]),
            "system_health": str(row[2]),
            "maintenance_mode": bool(row[3]),
            "last_updated": str(row[4]),
        }
        return [
            {
                "source": "system_status",
                "match_text": (
                    f"system status health load incidents maintenance operational "
                    f"{record['system_health']} {record['current_load_percentage']}"
                ),
                "record": record,
            }
        ]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        stopwords = {
            "a",
            "an",
            "and",
            "are",
            "can",
            "for",
            "how",
            "i",
            "is",
            "me",
            "of",
            "on",
            "our",
            "please",
            "tell",
            "the",
            "this",
            "to",
            "what",
            "when",
            "who",
            "why",
        }
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return [token for token in tokens if len(token) > 1 and token not in stopwords]

    def _score_candidate(self, query: str, query_tokens: List[str], match_text: str) -> int:
        candidate_tokens = set(self._tokenize(match_text))
        overlap = sum(1 for token in query_tokens if token in candidate_tokens)

        bonus = 0
        lowered_match = match_text.lower()
        for phrase in self._phrase_windows(query_tokens):
            if phrase in lowered_match:
                bonus = max(bonus, len(phrase.split()))

        if query in lowered_match:
            bonus += 2

        return overlap + bonus

    @staticmethod
    def _phrase_windows(tokens: List[str]) -> List[str]:
        phrases: List[str] = []
        for size in (3, 2):
            for index in range(0, max(len(tokens) - size + 1, 0)):
                phrases.append(" ".join(tokens[index : index + size]))
        return phrases
