"""Unit tests for tool behavior."""

import time
import unittest

from src.tools.external_api_tool import ExternalAPITool
from src.tools.guardrail_tool import GuardrailTool
from src.tools.structured_data_tool import StructuredDataTool


class _FakeCursor:
    def __init__(self, responses):
        self._responses = responses
        self._key = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        query_lower = query.lower()
        if "from intern_task.sla_lookup" in query_lower:
            self._key = "sla"
        elif "from intern_task.policies" in query_lower:
            self._key = "policies"
        elif "from intern_task.accounts" in query_lower:
            self._key = "accounts"
        else:
            self._key = None

    def fetchall(self):
        if self._key is None:
            return []
        return list(self._responses.get(self._key, []))

    def fetchone(self):
        rows = self.fetchall()
        return rows[0] if rows else None


class _FakeConn:
    def __init__(self, responses):
        self._responses = responses

    def cursor(self):
        return _FakeCursor(self._responses)

    def close(self):
        return None


class StructuredDataToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = StructuredDataTool()
        self.tool._connect_live_db = lambda: _FakeConn(  # type: ignore[method-assign]
            {
                "sla": [
                    (
                        "Premium Support",
                        "Premium",
                        "1 hour",
                        "8 hours",
                        "24/7",
                        ["Email", "Phone", "Chat"],
                        True,
                    )
                ],
                "policies": [
                    (
                        "POL-001",
                        "Access Control Policy",
                        "Security",
                        "Defines how access is granted.",
                        ["Employee", "Manager", "Admin"],
                    )
                ],
                "accounts": [],
            }
        )

    def test_sla_query_success(self) -> None:
        result = self.tool.run({"query": "What is SLA for Premium Support?"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["service_name"], "Premium Support")

    def test_account_status_not_found(self) -> None:
        result = self.tool.run({"query": "Check account status for user 9999"})
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"].lower())

    def test_policy_lookup_success(self) -> None:
        result = self.tool.run({"query": "show policy for manager"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["role"], "Manager")
        self.assertGreaterEqual(len(result["data"]["policies"]), 1)

    def test_fallback_lookup_matches_service_without_sla_keyword(self) -> None:
        result = self.tool.search_relevant({"query": "How fast is Premium Support?"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "sla_lookup")
        self.assertEqual(result["data"]["record"]["service_name"], "Premium Support")


class ExternalAPIToolTests(unittest.TestCase):
    def test_external_api_success(self) -> None:
        tool = ExternalAPITool()
        result = tool.run({"query": "system load"})
        self.assertEqual(result["status"], "ok")
        self.assertIn("System load", result["message"])

    def test_external_api_failure_with_retry_fallback(self) -> None:
        events = []
        tool = ExternalAPITool(logger=lambda e, p: events.append((e, p)))
        result = tool.run(
            {
                "query": "system load",
                "simulate_failure": True,
                "max_retries": 2,
            }
        )
        self.assertEqual(result["status"], "fallback")
        retry_events = [entry for entry in events if entry[0] == "retry_attempt"]
        self.assertEqual(len(retry_events), 2)

    def test_external_api_timeout_fallback(self) -> None:
        tool = ExternalAPITool(sleeper=time.sleep)
        result = tool.run(
            {
                "query": "system load",
                "simulate_delay_seconds": 0.01,
                "timeout_seconds": 0.001,
                "max_retries": 0,
            }
        )
        self.assertEqual(result["status"], "fallback")
        self.assertIn("timed out", result["error"].lower())


class GuardrailToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = GuardrailTool()

    def test_guardrail_refuses_unsafe_query(self) -> None:
        result = self.tool.run({"query": "Delete all records immediately"})
        self.assertEqual(result["status"], "refused")
        self.assertTrue(result["escalation_required"])

    def test_guardrail_approves_safe_query(self) -> None:
        result = self.tool.run({"query": "What is SLA for Premium Support?"})
        self.assertEqual(result["status"], "approved")
        self.assertFalse(result["escalation_required"])


if __name__ == "__main__":
    unittest.main()
