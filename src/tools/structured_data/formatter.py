"""Response formatting helpers for structured data retrieval."""

from __future__ import annotations

from typing import Any, Dict, List


def group_candidates(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for candidate in candidates:
        source = str(candidate["source"])
        record = dict(candidate["record"])
        score = int(candidate.get("score", 0))
        grouped.setdefault(source, []).append({"record": record, "score": score})

    if len(grouped) == 1:
        source, entries = next(iter(grouped.items()))
        return _single_source_payload(source, entries)
    return _multi_source_payload(grouped)


def build_match_message(grouped: Dict[str, Any]) -> str:
    if "source" in grouped:
        if "records" in grouped:
            count = grouped.get("match_count", len(grouped.get("records", [])))
            return f"Found {count} matching rows from {grouped['source']}."
        return f"Found fallback structured data from {grouped['source']}."

    sources = grouped.get("sources", [])
    source_names = ", ".join(str(item.get("source", "unknown")) for item in sources)
    return f"Found structured data across {source_names}."


def success_response(data: Dict[str, Any], message: str) -> Dict[str, Any]:
    return {
        "status": "ok",
        "message": message,
        "data": data,
    }


def error_response(message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "message": message,
        "data": {},
    }


def _single_source_payload(source: str, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    records = [entry["record"] for entry in entries]
    scores = [entry["score"] for entry in entries]
    if len(records) == 1:
        return {
            "source": source,
            "record": records[0],
            "score": scores[0],
        }
    return {
        "source": source,
        "records": records,
        "scores": scores,
        "match_count": len(records),
    }


def _multi_source_payload(grouped: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    sources = [
        {
            "source": source,
            "records": [entry["record"] for entry in entries],
            "scores": [entry["score"] for entry in entries],
            "match_count": len(entries),
        }
        for source, entries in grouped.items()
    ]
    sources.sort(key=lambda item: max(item["scores"], default=0), reverse=True)
    return {
        "sources": sources,
        "match_count": sum(item["match_count"] for item in sources),
    }
