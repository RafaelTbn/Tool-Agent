"""Unit tests for structured logger behavior."""

import json
import unittest
from pathlib import Path

from src.logging import AgentLogger


class AgentLoggerTests(unittest.TestCase):
    def test_tools_logger_keeps_history_and_writes_jsonl_file(self) -> None:
        log_path = Path("tests/.tmp_agent_history.jsonl")
        if log_path.exists():
            log_path.unlink()

        logger = AgentLogger(name="tool_agent_test_logger", file_path=str(log_path))

        logger.log("decision_made", {"query": "hello", "action": "direct_answer"})
        logger.log("final_response", {"status": "ok", "message": "hi"})

        self.assertEqual(len(logger.get_history()), 2)
        self.assertTrue(log_path.exists())

        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 2)
        first_entry = json.loads(lines[0])
        self.assertEqual(first_entry["event"], "decision_made")
        self.assertEqual(first_entry["payload"]["action"], "direct_answer")

        log_path.unlink()


if __name__ == "__main__":
    unittest.main()
