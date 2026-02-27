"""Deterministic structured-data query tool."""

from __future__ import annotations

import re
from typing import Any, Dict, List


class StructuredDataTool:
    """Simulates internal database/policy/SLA lookups."""

    _SLA: Dict[str, Dict[str, Any]] = {
        "basic support": {
            "service_name": "Basic Support",
            "tier": "Basic",
            "response_time": "24 hours",
            "resolution_time": "3 business days",
            "availability": "Business hours (09:00-18:00)",
            "support_channels": ["Email"],
            "escalation_available": False,
        },
        "premium support": {
            "service_name": "Premium Support",
            "tier": "Premium",
            "response_time": "1 hour",
            "resolution_time": "8 hours",
            "availability": "24/7",
            "support_channels": ["Email", "Phone", "Chat"],
            "escalation_available": True,
        },
        "enterprise support": {
            "service_name": "Enterprise Support",
            "tier": "Enterprise",
            "response_time": "15 minutes",
            "resolution_time": "4 hours",
            "availability": "24/7 with dedicated manager",
            "support_channels": ["Dedicated Hotline", "Priority Email"],
            "escalation_available": True,
        },
    }

    _ACCOUNTS: Dict[str, Dict[str, Any]] = {
        "1001": {
            "user_id": "1001",
            "name": "Alice Tan",
            "role": "Employee",
            "status": "Active",
            "service_plan": "Basic Support",
            "last_login": "2026-02-17T10:15:00Z",
        },
        "1002": {
            "user_id": "1002",
            "name": "Brian Lim",
            "role": "Manager",
            "status": "Active",
            "service_plan": "Premium Support",
            "last_login": "2026-02-17T08:22:00Z",
        },
        "1003": {
            "user_id": "1003",
            "name": "Clara Wijaya",
            "role": "Admin",
            "status": "Suspended",
            "service_plan": "Enterprise Support",
            "last_login": "2026-02-10T19:03:00Z",
        },
    }

    _POLICIES: List[Dict[str, Any]] = [
        {
            "policy_id": "POL-001",
            "title": "Access Control Policy",
            "category": "Security",
            "role_scope": ["Employee", "Manager", "Admin"],
        },
        {
            "policy_id": "POL-002",
            "title": "Data Deletion Policy",
            "category": "Compliance",
            "role_scope": ["Admin"],
        },
        {
            "policy_id": "POL-003",
            "title": "Incident Escalation Policy",
            "category": "Operations",
            "role_scope": ["Support", "Manager"],
        },
    ]

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        query = self._normalize_query(params)

        if "sla" in query:
            return self._lookup_sla(query)
        if "policy" in query:
            return self._lookup_policy(query)
        if "account status" in query or "account" in query:
            return self._lookup_account(query)

        return {
            "status": "error",
            "message": "Unsupported structured query. Use SLA, policy, or account status.",
            "data": {},
        }

    @staticmethod
    def _normalize_query(params: Dict[str, Any]) -> str:
        query = params.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("structured_data_tool requires non-empty string 'query'.")
        return " ".join(query.lower().split())

    def _lookup_sla(self, query: str) -> Dict[str, Any]:
        for service_name, record in self._SLA.items():
            if service_name in query:
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

    def _lookup_policy(self, query: str) -> Dict[str, Any]:
        for role in ("employee", "manager", "admin", "support"):
            if role in query:
                role_title = role.capitalize()
                matches = [p for p in self._POLICIES if role_title in p["role_scope"]]
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

    def _lookup_account(self, query: str) -> Dict[str, Any]:
        matched = re.search(r"\b\d{3,}\b", query)
        if not matched:
            return {
                "status": "error",
                "message": "Account query must include numeric user id.",
                "data": {},
            }
        user_id = matched.group(0)
        account = self._ACCOUNTS.get(user_id)
        if account is None:
            return {
                "status": "error",
                "message": f"Account {user_id} not found.",
                "data": {},
            }
        return {
            "status": "ok",
            "message": f"Account {user_id} status is {account['status']}.",
            "data": account,
        }
