"""Unit tests for decision engine behavior."""

import unittest

from src.agent import DecisionEngine


class DecisionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DecisionEngine()

    def test_agent_flow_decide_guardrail_refuse(self) -> None:
        result = self.engine.decide("Delete all records immediately")
        self.assertEqual(result.action, "guardrail_refuse")

    def test_agent_flow_decide_structured_data_tool(self) -> None:
        result = self.engine.decide("What is the SLA for Premium Support?")
        self.assertEqual(result.action, "structured_data_tool")

    def test_agent_flow_decide_structured_data_tool_for_account_query(self) -> None:
        result = self.engine.decide("check account 1002")
        self.assertEqual(result.action, "structured_data_tool")

    def test_agent_flow_decide_external_api_tool(self) -> None:
        result = self.engine.decide("What is today's system load?")
        self.assertEqual(result.action, "external_api_tool")

    def test_agent_flow_decide_external_api_tool_for_weather(self) -> None:
        result = self.engine.decide("cuaca hari ini di jakarta")
        self.assertEqual(result.action, "external_api_tool")

    def test_agent_flow_decide_direct_answer(self) -> None:
        result = self.engine.decide("Hello there")
        self.assertEqual(result.action, "direct_answer")


if __name__ == "__main__":
    unittest.main()
