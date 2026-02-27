"""Unit tests for tool behavior."""

import time
import unittest

from src.tools.external_api_tool import ExternalAPITool
from src.tools.guardrail_tool import GuardrailTool
from src.tools.structured_data_tool import StructuredDataTool


class StructuredDataToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = StructuredDataTool()

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
