from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .agent import MultiMemoryAgent
from .memory import extract_episode
from .prompt import build_prompt
from .state import MemoryGraphState

try:  # pragma: no cover - optional dependency
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - fallback when langgraph is unavailable
    END = "__end__"
    START = "__start__"
    StateGraph = None


RouteFn = Callable[[MemoryGraphState], str]


def _latest_user_message(state: MemoryGraphState) -> str:
    messages = state.get("messages") or []
    if not messages:
        return ""
    return messages[-1]["content"]


def _route_for_message(user_message: str) -> str:
    lowered = user_message.lower()
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
            "task",
            "done",
            "xong",
            "completed",
            "finished",
            "resolved",
            "episode",
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
            "semantic",
            "note",
            "reminder",
            "check",
        ]
    ):
        return "semantic"
    return "recent"


@dataclass
class MemoryGraph:
    agent: MultiMemoryAgent
    compiled: Any = None
    route_fn: RouteFn = field(default=_route_for_message)

    def ingest_memory(self, state: MemoryGraphState) -> MemoryGraphState:
        user_message = _latest_user_message(state)
        retrieved_facts = self.agent.ingest_user_message(user_message)
        return {"retrieved_facts": retrieved_facts}

    def route_memory(self, state: MemoryGraphState) -> MemoryGraphState:
        user_message = _latest_user_message(state)
        return {"route": self.route_fn(user_message)}

    def _retrieve_scoped_memory(self, state: MemoryGraphState, route: str) -> MemoryGraphState:
        user_message = _latest_user_message(state)
        return self.agent.store.retrieve_by_route(user_message, route=route, budget=self.agent.memory_budget)

    def retrieve_profile(self, state: MemoryGraphState) -> MemoryGraphState:
        return self._retrieve_scoped_memory(state, "profile")

    def retrieve_episodic(self, state: MemoryGraphState) -> MemoryGraphState:
        return self._retrieve_scoped_memory(state, "episodic")

    def retrieve_semantic(self, state: MemoryGraphState) -> MemoryGraphState:
        return self._retrieve_scoped_memory(state, "semantic")

    def retrieve_recent(self, state: MemoryGraphState) -> MemoryGraphState:
        return self._retrieve_scoped_memory(state, "recent")

    def compose_response(self, state: MemoryGraphState) -> MemoryGraphState:
        user_message = _latest_user_message(state)
        context_sections = self.agent.store.context_manager.budget_sections(
            state.get("user_profile", {}),
            state.get("episodes", []),
            state.get("semantic_hits", []),
            state.get("recent_messages", []),
        )
        state["context_sections"] = context_sections
        prompt = build_prompt(user_message, state)
        assistant_message = self.agent.answer_from_memory(user_message, state)
        return {"prompt": prompt, "assistant_message": assistant_message, "context_sections": context_sections}

    def persist_memory(self, state: MemoryGraphState) -> MemoryGraphState:
        user_message = _latest_user_message(state)
        assistant_message = state.get("assistant_message", "")
        self.agent.commit_turn(user_message, assistant_message)
        episode = extract_episode(user_message)
        if episode:
            episode["summary"] = f"{episode['summary']} | assistant: {assistant_message}"
            state.setdefault("episodes", []).append(episode)
        return {}

    def invoke(self, input_state: MemoryGraphState | str) -> MemoryGraphState:
        if self.compiled is not None:
            if isinstance(input_state, str):
                input_state = {"messages": [{"role": "user", "content": input_state}]}
            return self.compiled.invoke(input_state)

        if isinstance(input_state, str):
            input_state = {"messages": [{"role": "user", "content": input_state}]}
        return self._fallback_invoke(input_state)

    def _fallback_invoke(self, state: MemoryGraphState) -> MemoryGraphState:
        self.ingest_memory(state)
        route = self.route_fn(_latest_user_message(state))
        state["route"] = route
        if route == "profile":
            state.update(self.retrieve_profile(state))
        elif route == "episodic":
            state.update(self.retrieve_episodic(state))
        elif route == "semantic":
            state.update(self.retrieve_semantic(state))
        else:
            state.update(self.retrieve_recent(state))
        state.update(self.compose_response(state))
        self.persist_memory(state)
        return state


def build_memory_graph(agent: MultiMemoryAgent | None = None) -> MemoryGraph:
    agent = agent or MultiMemoryAgent()
    if StateGraph is None:
        return MemoryGraph(agent=agent)

    graph = StateGraph(MemoryGraphState)
    runtime = MemoryGraph(agent=agent)

    graph.add_node("ingest_memory", runtime.ingest_memory)
    graph.add_node("route_memory", runtime.route_memory)
    graph.add_node("retrieve_profile", runtime.retrieve_profile)
    graph.add_node("retrieve_episodic", runtime.retrieve_episodic)
    graph.add_node("retrieve_semantic", runtime.retrieve_semantic)
    graph.add_node("retrieve_recent", runtime.retrieve_recent)
    graph.add_node("compose_response", runtime.compose_response)
    graph.add_node("persist_memory", runtime.persist_memory)

    graph.add_edge(START, "ingest_memory")
    graph.add_edge("ingest_memory", "route_memory")
    graph.add_conditional_edges(
        "route_memory",
        lambda state: state.get("route", "recent"),
        {
            "profile": "retrieve_profile",
            "episodic": "retrieve_episodic",
            "semantic": "retrieve_semantic",
            "recent": "retrieve_recent",
        },
    )
    graph.add_edge("retrieve_profile", "compose_response")
    graph.add_edge("retrieve_episodic", "compose_response")
    graph.add_edge("retrieve_semantic", "compose_response")
    graph.add_edge("retrieve_recent", "compose_response")
    graph.add_edge("compose_response", "persist_memory")
    graph.add_edge("persist_memory", END)

    runtime.compiled = graph.compile()
    return runtime
