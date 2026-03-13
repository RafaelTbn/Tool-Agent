"""Unit tests for tool behavior."""

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
        self.assertEqual(result["data"]["source"], "sla_lookup")
        self.assertEqual(result["data"]["record"]["service_name"], "Premium Support")

    def test_account_status_matches_account_record(self) -> None:
        self.tool._connect_live_db = lambda: _FakeConn(  # type: ignore[method-assign]
            {
                "sla": [],
                "policies": [],
                "accounts": [
                    ("1002", "Brian Lim", "Manager", "Active", "Premium Support", "2026-02-17T08:22:00Z")
                ],
            }
        )
        result = self.tool.run({"query": "Check account status for user 1002"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "accounts")
        self.assertEqual(result["data"]["record"]["user_id"], "1002")

    def test_account_query_supports_multiple_rows(self) -> None:
        self.tool._connect_live_db = lambda: _FakeConn(  # type: ignore[method-assign]
            {
                "sla": [],
                "policies": [],
                "accounts": [
                    ("1001", "Alice Tan", "Employee", "Active", "Basic Support", "2026-02-17T10:15:00Z"),
                    ("1002", "Brian Lim", "Manager", "Active", "Premium Support", "2026-02-17T08:22:00Z"),
                    ("1003", "Clara Wijaya", "Admin", "Suspended", "Enterprise Support", "2026-02-10T19:03:00Z"),
                ],
            }
        )
        result = self.tool.run({"query": "what name and role on user id 1001, 1002 and 1003?"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "accounts")
        self.assertEqual(result["data"]["match_count"], 3)
        self.assertEqual(len(result["data"]["records"]), 3)

    def test_policy_lookup_success(self) -> None:
        result = self.tool.run({"query": "show policy for manager"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "policies")
        self.assertEqual(result["data"]["record"]["policy_id"], "POL-001")
        self.assertIn("Manager", result["data"]["record"]["role_scope"])

    def test_query_can_return_mixed_sources(self) -> None:
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
        result = self.tool.run({"query": "compare premium support and manager policy"})
        self.assertEqual(result["status"], "ok")
        self.assertIn("sources", result["data"])
        source_names = {item["source"] for item in result["data"]["sources"]}
        self.assertIn("sla_lookup", source_names)
        self.assertIn("policies", source_names)

    def test_fallback_lookup_matches_service_without_sla_keyword(self) -> None:
        result = self.tool.search_relevant({"query": "How fast is Premium Support?"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "sla_lookup")
        self.assertEqual(result["data"]["record"]["service_name"], "Premium Support")


class ExternalAPIToolTests(unittest.TestCase):
    class _FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP {self.status_code}")

        def json(self):
            return self._payload

    class _FakeRequester:
        def __init__(self, responses):
            self._responses = responses

        def get(self, url, params=None, timeout=None):
            if "geocoding-api" in url:
                payload = self._responses["geocode"]
            else:
                payload = self._responses["forecast"]
            if isinstance(payload, Exception):
                raise payload
            return ExternalAPIToolTests._FakeResponse(payload)

    def test_external_api_success(self) -> None:
        tool = ExternalAPITool(
            requester=self._FakeRequester(
                {
                    "geocode": {
                        "results": [
                            {
                                "name": "Jakarta",
                                "country": "Indonesia",
                                "latitude": -6.175,
                                "longitude": 106.827,
                            }
                        ]
                    },
                    "forecast": {
                        "current": {
                            "temperature_2m": 31.2,
                            "apparent_temperature": 35.0,
                            "relative_humidity_2m": 74,
                            "weather_code": 2,
                            "wind_speed_10m": 12.4,
                        }
                    },
                }
            )
        )
        result = tool.run({"query": "cuaca hari ini di jakarta"})
        self.assertEqual(result["status"], "ok")
        self.assertIn("Jakarta", result["message"])
        self.assertEqual(result["data"]["condition"], "Partly cloudy")

    def test_external_api_failure_with_retry_fallback(self) -> None:
        events = []
        tool = ExternalAPITool(
            logger=lambda e, p: events.append((e, p)),
            requester=self._FakeRequester({"geocode": ConnectionError("boom"), "forecast": {}}),
        )
        result = tool.run(
            {
                "query": "cuaca di jakarta",
                "max_retries": 2,
            }
        )
        self.assertEqual(result["status"], "fallback")
        retry_events = [entry for entry in events if entry[0] == "retry_attempt"]
        self.assertEqual(len(retry_events), 2)

    def test_external_api_timeout_fallback(self) -> None:
        class SlowRequester:
            def get(self, url, params=None, timeout=None):
                import time

                if "geocoding-api" in url:
                    return ExternalAPIToolTests._FakeResponse(
                        {
                            "results": [
                                {
                                    "name": "Jakarta",
                                    "country": "Indonesia",
                                    "latitude": -6.175,
                                    "longitude": 106.827,
                                }
                            ]
                        }
                    )

                time.sleep(0.01)
                return ExternalAPIToolTests._FakeResponse(
                    {
                        "current": {
                            "temperature_2m": 30,
                            "apparent_temperature": 33,
                            "relative_humidity_2m": 70,
                            "weather_code": 1,
                            "wind_speed_10m": 10,
                        }
                    }
                )

        tool = ExternalAPITool(requester=SlowRequester())
        result = tool.run(
            {
                "query": "cuaca di jakarta",
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
