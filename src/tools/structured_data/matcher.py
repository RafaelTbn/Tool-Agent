"""Matching and ranking helpers for structured data retrieval."""

from __future__ import annotations

import re
from typing import Any, Dict, List


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "for",
    "how",
    "i",
    "is",
    "me",
    "of",
    "on",
    "our",
    "please",
    "tell",
    "the",
    "this",
    "to",
    "what",
    "when",
    "who",
    "why",
}
ROLE_KEYWORDS = {"employee", "manager", "admin", "support"}
SYSTEM_KEYWORDS = ("system status", "system load", "health", "incidents", "maintenance")
EXPLICIT_MATCH_SCORE = 100


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) > 1 and token not in STOPWORDS]


def match_candidates(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    explicit_matches = _match_explicit_candidates(query, candidates)
    if explicit_matches:
        return explicit_matches
    return _select_ranked_candidates(query, tokenize(query), candidates)


def _match_explicit_candidates(query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    matched: List[Dict[str, Any]] = []
    user_ids = set(re.findall(r"\b\d{3,}\b", query))
    query_tokens = set(tokenize(query))

    for candidate in candidates:
        source = candidate["source"]
        record = candidate["record"]
        if source == "accounts" and record.get("user_id") in user_ids:
            matched.append(_with_score(candidate, EXPLICIT_MATCH_SCORE))
            continue
        if source == "sla_lookup" and str(record.get("service_name", "")).lower() in query:
            matched.append(_with_score(candidate, EXPLICIT_MATCH_SCORE))
            continue
        if source == "policies" and _matches_policy(query, query_tokens, record):
            matched.append(_with_score(candidate, EXPLICIT_MATCH_SCORE))
            continue
        if source == "system_status" and any(keyword in query for keyword in SYSTEM_KEYWORDS):
            matched.append(_with_score(candidate, EXPLICIT_MATCH_SCORE))

    return deduplicate_candidates(matched)


def _matches_policy(query: str, query_tokens: set[str], record: Dict[str, Any]) -> bool:
    role_scope = {value.lower() for value in record.get("role_scope", [])}
    if ROLE_KEYWORDS.intersection(role_scope).intersection(query_tokens):
        return True
    policy_id = str(record.get("policy_id", "")).lower()
    title = str(record.get("title", "")).lower()
    return bool((policy_id and policy_id in query) or (title and title in query))


def _select_ranked_candidates(
    query: str,
    query_tokens: List[str],
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    scored = [
        _with_score(candidate, score)
        for candidate in candidates
        for score in [_score_candidate(query, query_tokens, candidate["match_text"])]
        if score >= 2
    ]
    scored.sort(key=lambda item: int(item["score"]), reverse=True)
    return deduplicate_candidates(scored[:5])


def _score_candidate(query: str, query_tokens: List[str], match_text: str) -> int:
    candidate_tokens = set(tokenize(match_text))
    overlap = sum(1 for token in query_tokens if token in candidate_tokens)

    bonus = 0
    lowered_match = match_text.lower()
    for phrase in _phrase_windows(query_tokens):
        if phrase in lowered_match:
            bonus = max(bonus, len(phrase.split()))

    if query in lowered_match:
        bonus += 2
    return overlap + bonus


def deduplicate_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique: List[Dict[str, Any]] = []
    for candidate in candidates:
        key = _candidate_key(str(candidate.get("source")), candidate.get("record", {}))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _candidate_key(source: str, record: Dict[str, Any]) -> tuple[str, str]:
    if source == "accounts":
        return source, str(record.get("user_id", ""))
    if source == "sla_lookup":
        return source, str(record.get("service_name", ""))
    if source == "policies":
        return source, str(record.get("policy_id", ""))
    return source, str(record)


def _with_score(candidate: Dict[str, Any], score: int) -> Dict[str, Any]:
    enriched = dict(candidate)
    enriched["score"] = score
    return enriched


def _phrase_windows(tokens: List[str]) -> List[str]:
    phrases: List[str] = []
    for size in (3, 2):
        for index in range(0, max(len(tokens) - size + 1, 0)):
            phrases.append(" ".join(tokens[index : index + size]))
    return phrases
