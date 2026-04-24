from __future__ import annotations

from .state import MemoryState


def build_prompt(user_message: str, state: MemoryState) -> str:
    profile = state.get("user_profile", {})
    episodes = state.get("episodes", [])
    semantic_hits = state.get("semantic_hits", [])
    recent_messages = state.get("recent_messages", [])
    sections = state.get("context_sections", {})
    memory_scope = state.get("memory_scope", "all")
    selected_memory_types = ", ".join(state.get("selected_memory_types", [])) or "none"

    profile_lines = "\n".join(f"- {key}: {value}" for key, value in profile.items()) or "- none"
    episode_lines = "\n".join(
        f"- {episode.get('title', 'episode')}: {episode.get('summary', '')} ({episode.get('outcome', '')})"
        for episode in episodes
    ) or "- none"
    semantic_lines = "\n".join(f"- {hit}" for hit in semantic_hits) or "- none"
    recent_lines = "\n".join(f"- {msg['role']}: {msg['content']}" for msg in recent_messages) or "- none"

    return (
        "Bạn là trợ lý có bộ nhớ.\n\n"
        f"Phạm vi truy xuất: {memory_scope}\n"
        f"Loại bộ nhớ đã nạp: {selected_memory_types}\n\n"
        "Bộ nhớ hồ sơ:\n"
        f"{sections.get('profile_text', profile_lines)}\n\n"
        "Bộ nhớ sự kiện:\n"
        f"{sections.get('episode_text', episode_lines)}\n\n"
        "Bộ nhớ ngữ nghĩa:\n"
        f"{sections.get('semantic_text', semantic_lines)}\n\n"
        "Đoạn hội thoại gần đây:\n"
        f"{sections.get('recent_text', recent_lines)}\n\n"
        f"Ước lượng token: {sections.get('token_estimate', 0)}\n\n"
        "Tin nhắn người dùng:\n"
        f"{user_message}\n"
    )
