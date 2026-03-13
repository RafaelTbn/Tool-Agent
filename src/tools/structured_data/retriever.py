"""Database retrieval helpers for structured data."""

from __future__ import annotations

from typing import Any, Dict, List


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


def _collect_sla_candidates(conn: Any, schema: str) -> List[Dict[str, Any]]:
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
            FROM {schema}.sla_lookup
            """
        )
        rows = cur.fetchall()

    return [
        {
            "source": "sla_lookup",
            "match_text": " ".join(
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
            "record": {
                "service_name": str(row[0]),
                "tier": str(row[1]),
                "response_time": str(row[2]),
                "resolution_time": str(row[3]),
                "availability": str(row[4]),
                "support_channels": list(row[5]),
                "escalation_available": bool(row[6]),
            },
        }
        for row in rows
    ]


def _collect_policy_candidates(conn: Any, schema: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT p.policy_id, p.title, p.category, p.description, p.role_scope, pr.rule_text
            FROM {schema}.policies p
            LEFT JOIN {schema}.policy_rules pr
                ON p.policy_id = pr.policy_id
            ORDER BY p.policy_id, pr.rule_order
            """
        )
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
        for record in grouped.values()
    ]


def _collect_account_candidates(conn: Any, schema: str) -> List[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT user_id, name, role, status, service_plan, last_login
            FROM {schema}.accounts
            """
        )
        rows = cur.fetchall()

    return [
        {
            "source": "accounts",
            "match_text": " ".join(
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
            "record": {
                "user_id": str(row[0]),
                "name": str(row[1]),
                "role": str(row[2]),
                "status": str(row[3]),
                "service_plan": str(row[4]),
                "last_login": str(row[5]),
            },
        }
        for row in rows
    ]


def _collect_system_status_candidates(conn: Any, schema: str) -> List[Dict[str, Any]]:
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
        {
            "source": "system_status",
            "match_text": (
                f"system status health load incidents maintenance operational "
                f"{record['system_health']} {record['current_load_percentage']}"
            ),
            "record": record,
        }
    ]
