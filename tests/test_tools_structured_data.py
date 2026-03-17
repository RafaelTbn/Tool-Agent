"""Unit tests for structured data tool behavior."""

import unittest

from src.tools.structured_data_tool import StructuredDataTool

from tests.support import FakeConn


class StructuredDataToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = StructuredDataTool()
        self.tool._connect_live_db = lambda: FakeConn(  # type: ignore[method-assign]
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

    def test_tools_sla_query_success(self) -> None:
        result = self.tool.run({"query": "What is SLA for Premium Support?"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "sla_lookup")
        self.assertEqual(result["data"]["record"]["service_name"], "Premium Support")

    def test_tools_account_status_matches_account_record(self) -> None:
        self.tool._connect_live_db = lambda: FakeConn(  # type: ignore[method-assign]
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

    def test_tools_account_query_supports_multiple_rows(self) -> None:
        self.tool._connect_live_db = lambda: FakeConn(  # type: ignore[method-assign]
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

    def test_tools_policy_lookup_success(self) -> None:
        result = self.tool.run({"query": "show policy for manager"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "policies")
        self.assertEqual(result["data"]["record"]["policy_id"], "POL-001")
        self.assertIn("Manager", result["data"]["record"]["role_scope"])

    def test_tools_query_can_return_mixed_sources(self) -> None:
        self.tool._connect_live_db = lambda: FakeConn(  # type: ignore[method-assign]
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

    def test_tools_fallback_lookup_matches_service_without_sla_keyword(self) -> None:
        result = self.tool.search_relevant({"query": "How fast is Premium Support?"})
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["data"]["source"], "sla_lookup")
        self.assertEqual(result["data"]["record"]["service_name"], "Premium Support")


if __name__ == "__main__":
    unittest.main()
