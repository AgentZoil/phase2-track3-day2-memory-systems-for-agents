from __future__ import annotations

import re

from .backends import MemoryStore, normalize_text, utc_now


FACT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("name", re.compile(r"(?:my name is|t[oô]i t[eê]n l[aà](?: l[aà])?)\s+([^\.,;]+)", re.IGNORECASE)),
    ("location", re.compile(r"(?:i live in|t[oô]i s[oố]ng ở|t[oô]i s[oố]ng t[aạ]i|t[oô]i ở)\s+([^\.,;]+)", re.IGNORECASE)),
    ("allergy", re.compile(r"(?:i am allergic to|t[oô]i d[iị]\s*[uư]ng)\s+([^\.,;]+)", re.IGNORECASE)),
    ("preference", re.compile(r"(?:i like|t[oô]i th[ií]ch)\s+([^\.,;]+)", re.IGNORECASE)),
]


def strip_clauses(value: str) -> str:
    value = value.strip()
    value = re.sub(r"\s+ch[uứ]\s*kh[oô]ng\s+ph[aả]i.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+(?:kh[oô]ng|not)\s+ph[aả]i.*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"[.!?]+$", "", value)
    return value.strip()


def extract_facts(text: str) -> dict[str, str]:
    lowered = text.lower()
    facts: dict[str, str] = {}

    question_markers = [
        "tôi tên là gì",
        "tên tôi là gì",
        "tôi dị ứng gì",
        "tôi sống ở đâu",
        "tôi thích gì",
        "ở đâu",
        "là gì",
    ]
    if "?" in text and any(marker in lowered for marker in question_markers):
        return facts

    allergy_prefixes = ["tôi dị ứng", "i am allergic to"]
    for prefix in allergy_prefixes:
        start = lowered.find(prefix)
        if start != -1:
            value = text[start + len(prefix) :]
            value = re.split(r"(?:ch[uứ]\s*kh[oô]ng\s+ph[aả]i|kh[oô]ng\s+ph[aả]i)", value, maxsplit=1, flags=re.IGNORECASE)[0]
            facts["allergy"] = strip_clauses(value)
            break

    for key, pattern in FACT_PATTERNS:
        match = pattern.search(text)
        if match:
            facts[key] = strip_clauses(match.group(1))

    return facts


def extract_episode(text: str) -> dict[str, str] | None:
    lowered = text.lower()
    if any(token in lowered for token in ["done", "completed", "xong", "hoàn thành", "finished", "resolved"]):
        return {
            "title": "Completed task",
            "summary": text,
            "outcome": "task_completed",
            "created_at": utc_now(),
        }
    return None


def detect_intent(text: str) -> str:
    lowered = text.lower()
    if any(
        token in lowered
        for token in [
            "name",
            "tên",
            "live",
            "ở đâu",
            "allergic",
            "dị ứng",
            "allergy",
            "preference",
            "prefer",
            "thích",
            "like",
            "sở thích",
            "hobby",
        ]
    ):
        return "profile"
    if any(
        token in lowered
        for token in [
            "done",
            "completed",
            "finished",
            "resolved",
            "xong",
            "task",
            "lesson",
            "bài học",
            "debug",
            "learned",
            "học được",
            "lần trước",
            "previous",
        ]
    ):
        return "episodic"
    if any(
        token in lowered
        for token in [
            "faq",
            "document",
            "chunk",
            "docker",
            "compose",
            "service",
            "note",
            "semantic",
            "reminder",
            "check",
        ]
    ):
        return "semantic"
    return "recent"


__all__ = [
    "MemoryStore",
    "detect_intent",
    "extract_episode",
    "extract_facts",
    "normalize_text",
    "strip_clauses",
]
