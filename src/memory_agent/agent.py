from __future__ import annotations

from dataclasses import dataclass, field

from .memory import MemoryStore, detect_intent, extract_episode, extract_facts
from .prompt import build_prompt
from .state import MemoryState


@dataclass
class MultiMemoryAgent:
    store: MemoryStore = field(default_factory=MemoryStore)
    memory_budget: int = 8

    def ingest_user_message(self, user_message: str) -> dict[str, str]:
        facts = extract_facts(user_message)
        for key, value in facts.items():
            self.store.profile.update(key, value, source=user_message)
        self.store.short_term.append("user", user_message)
        return facts

    def retrieve_memory(self, user_message: str) -> MemoryState:
        return self.store.retrieve(user_message, budget=self.memory_budget)

    def commit_turn(self, user_message: str, assistant_message: str) -> None:
        episode = extract_episode(user_message)
        if episode:
            episode["assistant_message"] = assistant_message
            self.store.append_episode(episode)

        self.store.short_term.append("assistant", assistant_message)

    def answer_from_memory(self, user_message: str, state: MemoryState) -> str:
        profile = state.get("user_profile", {})
        lower = user_message.lower()
        intent = detect_intent(user_message)
        parts: list[str] = []

        if intent == "profile" and ("tên" in lower or "name" in lower):
            if profile.get("name"):
                parts.append(f"Tôi nhớ tên bạn là {profile['name']}.")
        if intent == "profile" and ("dị ứng" in lower or "allergic" in lower):
            allergy = profile.get("allergy")
            if allergy:
                parts.append(f"Tôi nhớ bạn dị ứng {allergy}.")
        if intent == "profile" and ("ở đâu" in lower or "live" in lower or "nơi ở" in lower):
            location = profile.get("location")
            if location:
                parts.append(f"Tôi nhớ bạn sống ở {location}.")
        if intent == "profile" and ("thích" in lower or "preference" in lower or "like" in lower):
            preference = profile.get("preference")
            if preference:
                parts.append(f"Tôi nhớ bạn thích {preference}.")

        if parts:
            return " ".join(parts)

        if intent == "semantic" and state.get("semantic_hits"):
            return f"Tôi tìm thấy ghi chú liên quan: {state['semantic_hits'][0]}"

        if intent == "episodic" and state.get("episodes"):
            episode = state["episodes"][0]
            return f"Từ bộ nhớ, tác vụ liên quan gần nhất là: {episode.get('summary', '')}"

        if state.get("semantic_hits"):
            return f"Tôi tìm thấy ghi chú liên quan: {state['semantic_hits'][0]}"

        if state.get("episodes"):
            episode = state["episodes"][0]
            return f"Từ bộ nhớ, tác vụ liên quan gần nhất là: {episode.get('summary', '')}"

        if profile:
            return "Tôi đã lưu một phần thông tin, nhưng chưa đủ để trả lời chính xác."

        return "Tôi chưa có đủ bộ nhớ cho việc đó."

    def invoke(self, user_message: str) -> dict[str, str]:
        self.ingest_user_message(user_message)
        state = self.retrieve_memory(user_message)
        prompt = build_prompt(user_message, state)
        assistant_message = self.answer_from_memory(user_message, state)
        self.commit_turn(user_message, assistant_message)
        return {
            "prompt": prompt,
            "assistant_message": assistant_message,
        }
