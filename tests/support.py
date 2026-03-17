"""Shared test helpers."""

from __future__ import annotations


class FakeCursor:
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


class FakeConn:
    def __init__(self, responses):
        self._responses = responses

    def cursor(self):
        return FakeCursor(self._responses)

    def close(self):
        return None
