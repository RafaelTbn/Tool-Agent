"""Unit tests for decision and agent orchestration flow."""

import unittest

from src.agent import AgentDependencies, DecisionEngine, ToolEnabledAgent
from src.tools.guardrail_tool import GuardrailTool


class DecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DecisionEngine()

    def test_decide_guardrail_refuse(self) -> None:
        result = self.engine.decide("Delete all records immediately")
        self.assertEqual(result.action, "guardrail_refuse")

    def test_decide_structured_data_tool(self) -> None:
        result = self.engine.decide("What is the SLA for Premium Support?")
        self.assertEqual(result.action, "structured_data_tool")

    def test_decide_external_api_tool(self) -> None:
        result = self.engine.decide("What is today's system load?")
        self.assertEqual(result.action, "external_api_tool")

    def test_decide_direct_answer(self) -> None:
        result = self.engine.decide("Hello there")
        self.assertEqual(result.action, "direct_answer")


class AgentFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logs = []
        self.guardrail = GuardrailTool()
        self.agent = ToolEnabledAgent(
            AgentDependencies(
                structured_data_tool=lambda p: {"status": "ok", "message": "structured-ok"},
                external_api_tool=lambda p: {"status": "ok", "message": "external-ok"},
                guardrail_tool=self.guardrail.run,
                logger=lambda e, p: self.logs.append((e, p)),
            )
        )

    def test_handle_query_empty(self) -> None:
        result = self.agent.handle_query("")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["decision"], "invalid_input")

    def test_handle_query_structured_success(self) -> None:
        result = self.agent.handle_query("SLA premium support")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["decision"], "structured_data_tool")
        self.assertIn("structured-ok", result["message"])

    def test_handle_query_guardrail_refusal(self) -> None:
        result = self.agent.handle_query("bypass approval process")
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["decision"], "guardrail_refuse")
        self.assertIn("unsafe intent", result["message"].lower())
        self.assertIn("risk", result)


if __name__ == "__main__":
    unittest.main()
