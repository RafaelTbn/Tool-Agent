"""Database retrieval helpers for structured data."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Iterable, List, Optional


def connect_live_db(config: Dict[str, Any]) -> Any | None:
    try:
        import psycopg  # type: ignore
    except Exception:
        return None

    try:
        dsn = str(config.get("db_dsn", "")).strip()
        if dsn:
            return psycopg.connect(dsn, connect_timeout=int(config["db_connect_timeout"]))
        return psycopg.connect(
            host=config["db_host"],
            port=int(config["db_port"]),
            dbname=config["db_name"],
            user=config["db_user"],
            password=config["db_password"],
            connect_timeout=int(config["db_connect_timeout"]),
        )
    except Exception:
        return None


def collect_all_candidates(conn: Any, schema: str) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    candidates.extend(_collect_sla_candidates(conn, schema))
    candidates.extend(_collect_policy_candidates(conn, schema))
    candidates.extend(_collect_account_candidates(conn, schema))
    candidates.extend(_collect_system_status_candidates(conn, schema))
    return candidates


def collect_candidates_by_sources(
    conn: Any,
    schema: str,
    sources: Iterable[str],
    query_hints: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    collectors: Dict[str, Callable[[Any, str, Optional[Dict[str, Any]]], List[Dict[str, Any]]]] = {
        "sla_lookup": _collect_sla_candidates,
        "policies": _collect_policy_candidates,
        "accounts": _collect_account_candidates,
        "system_status": _collect_system_status_candidates,
    }

    candidates: List[Dict[str, Any]] = []
    for source in sources:
        collector = collectors.get(source)
        if collector is not None:
            candidates.extend(collector(conn, schema, query_hints))
    return candidates


def _collect_sla_candidates(
    conn: Any,
    schema: str,
    query_hints: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    query = f"""
            SELECT
                service_name,
                tier,
                response_time,
                resolution_time,
                availability,
                support_channels,
                escalation_available
            FROM {schema}.sla_lookup
            """
    params: List[Any] = []
    service_terms = list((query_hints or {}).get("service_terms", []))
    if service_terms:
        query += """
            WHERE LOWER(service_name) LIKE ANY(%s)
               OR LOWER(tier) LIKE ANY(%s)
            """
        patterns = [f"%{term}%" for term in service_terms]
        params.extend([patterns, patterns])

    with conn.cursor() as cur:
        cur.execute(query, params or None)
        rows = cur.fetchall()

    return [
        _build_candidate(
            "sla_lookup",
            " ".join(
                [
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    str(row[3]),
                    str(row[4]),
                    " ".join(list(row[5])),
                    "service support plan",
                ]
            ),
            {
                "service_name": str(row[0]),
                "tier": str(row[1]),
                "response_time": str(row[2]),
                "resolution_time": str(row[3]),
                "availability": str(row[4]),
                "support_channels": list(row[5]),
                "escalation_available": bool(row[6]),
            },
        )
        for row in rows
    ]


def _collect_policy_candidates(
    conn: Any,
    schema: str,
    query_hints: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    query = f"""
            SELECT p.policy_id, p.title, p.category, p.description, p.role_scope, pr.rule_text
            FROM {schema}.policies p
            LEFT JOIN {schema}.policy_rules pr
                ON p.policy_id = pr.policy_id
            """
    params: List[Any] = []
    policy_terms = [
        term
        for term in (query_hints or {}).get("policy_terms", [])
        if term not in {"policy", "policies"}
    ]
    if policy_terms:
        query += """
            WHERE LOWER(p.title) LIKE ANY(%s)
               OR LOWER(p.policy_id) LIKE ANY(%s)
               OR EXISTS (
                    SELECT 1
                    FROM unnest(p.role_scope) AS role_name
                    WHERE LOWER(role_name) = ANY(%s)
               )
            """
        patterns = [f"%{term}%" for term in policy_terms]
        params.extend([patterns, patterns, policy_terms])
    query += """
            ORDER BY p.policy_id, pr.rule_order
            """

    with conn.cursor() as cur:
        cur.execute(query, params or None)
        rows = cur.fetchall()

    grouped: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        policy_id = str(row[0])
        policy = grouped.setdefault(
            policy_id,
            {
                "policy_id": policy_id,
                "title": str(row[1]),
                "category": str(row[2]),
                "description": str(row[3]),
                "role_scope": list(row[4]),
                "rules": [],
            },
        )
        if len(row) > 5 and row[5] is not None:
            policy["rules"].append(str(row[5]))

    return [
        _build_candidate(
            "policies",
            " ".join(
                [
                    record["policy_id"],
                    record["title"],
                    record["category"],
                    record["description"],
                    " ".join(record["role_scope"]),
                    " ".join(record["rules"]),
                ]
            ),
            record,
        )
        for record in grouped.values()
    ]


def _collect_account_candidates(
    conn: Any,
    schema: str,
    query_hints: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    query = f"""
            SELECT user_id, name, role, status, service_plan, last_login
            FROM {schema}.accounts
            """
    params: List[Any] = []
    user_ids = list((query_hints or {}).get("user_ids", []))
    if user_ids:
        query += """
            WHERE user_id = ANY(%s)
            """
        params.append(user_ids)

    with conn.cursor() as cur:
        cur.execute(query, params or None)
        rows = cur.fetchall()

    return [
        _build_candidate(
            "accounts",
            " ".join(
                [
                    "account user status service plan login",
                    str(row[0]),
                    str(row[1]),
                    str(row[2]),
                    str(row[3]),
                    str(row[4]),
                    str(row[5]),
                ]
            ),
            {
                "user_id": str(row[0]),
                "name": str(row[1]),
                "role": str(row[2]),
                "status": str(row[3]),
                "service_plan": str(row[4]),
                "last_login": str(row[5]),
            },
        )
        for row in rows
    ]


def _collect_system_status_candidates(
    conn: Any,
    schema: str,
    query_hints: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT current_load_percentage, active_incidents, system_health, maintenance_mode, last_updated
            FROM {schema}.system_status
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
        _build_candidate(
            "system_status",
            (
                f"system status health load incidents maintenance operational "
                f"{record['system_health']} {record['current_load_percentage']}"
            ),
            record,
        )
    ]


def _build_candidate(source: str, match_text: str, record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source": source,
        "match_text": match_text,
        "match_tokens": _tokenize_match_text(match_text),
        "record": record,
    }


def _tokenize_match_text(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())
