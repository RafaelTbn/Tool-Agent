"""Unit tests for guardrail tool behavior."""

import unittest

from src.tools.guardrail_tool import GuardrailTool


class GuardrailToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = GuardrailTool()

    def test_tools_guardrail_refuses_unsafe_query(self) -> None:
        result = self.tool.run({"query": "Delete all records immediately"})
        self.assertEqual(result["status"], "refused")
        self.assertTrue(result["escalation_required"])

    def test_tools_guardrail_approves_safe_query(self) -> None:
        result = self.tool.run({"query": "What is SLA for Premium Support?"})
        self.assertEqual(result["status"], "approved")
        self.assertFalse(result["escalation_required"])


if __name__ == "__main__":
    unittest.main()
