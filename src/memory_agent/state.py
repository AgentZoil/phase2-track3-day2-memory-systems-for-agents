from __future__ import annotations

from typing import TypedDict


class MemoryState(TypedDict, total=False):
    messages: list[dict[str, str]]
    user_profile: dict[str, str]
    episodes: list[dict[str, str]]
    semantic_hits: list[str]
    memory_budget: int
    recent_messages: list[dict[str, str]]
    retrieved_facts: dict[str, str]
    route: str
    memory_scope: str
    selected_memory_types: list[str]
    prompt: str
    assistant_message: str


class MemoryGraphState(MemoryState, total=False):
    pass
