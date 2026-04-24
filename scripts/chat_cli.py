from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from memory_agent import build_memory_graph
from memory_agent.openai_llm import OpenAIResponder, _load_dotenv
from memory_agent.prompt import build_prompt


def format_memory_snapshot(state: dict[str, object]) -> str:
    profile = state.get("user_profile", {}) or {}
    episodes = state.get("episodes", []) or []
    semantic_hits = state.get("semantic_hits", []) or []
    recent_messages = state.get("recent_messages", []) or []
    context_sections = state.get("context_sections", {}) or {}
    context_tokens = context_sections.get("context_tokens", {}) if isinstance(context_sections, dict) else {}
    memory_scope = state.get("memory_scope", "all")
    selected_memory_types = state.get("selected_memory_types", []) or []

    profile_lines = ", ".join(f"{k}={v}" for k, v in profile.items()) if profile else "none"
    episode_lines = (
        "; ".join(f"{ep.get('title', 'episode')}: {ep.get('summary', '')}" for ep in episodes[-3:])
        if episodes
        else "none"
    )
    semantic_lines = ", ".join(str(hit) for hit in semantic_hits) if semantic_hits else "none"
    recent_lines = (
        "; ".join(f"{msg.get('role', '?')}: {msg.get('content', '')}" for msg in recent_messages[-4:])
        if recent_messages
        else "none"
    )

    return (
        "Memory snapshot\n"
        f"- scope: {memory_scope}\n"
        f"- selected: {', '.join(selected_memory_types) if selected_memory_types else 'none'}\n"
        f"- profile: {profile_lines}\n"
        f"- episodes: {episode_lines}\n"
        f"- semantic_hits: {semantic_lines}\n"
        f"- recent: {recent_lines}\n"
        f"- context_tokens: {context_tokens}\n"
        f"- token_estimate: {context_sections.get('token_estimate', 0) if isinstance(context_sections, dict) else 0}"
    )


def main() -> None:
    runtime_dir = ROOT / "data" / "chat_cli_runtime"
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    os.environ["MEMORY_DATA_DIR"] = str(runtime_dir)
    _load_dotenv(ROOT / ".env")
    app = build_memory_graph()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    try:
        responder = OpenAIResponder(model=model)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print("Memory chat CLI")
    print("Type your message and press Enter.")
    print("Commands: /exit, /quit, /reset")
    print(f"OpenAI model: {model}")

    session_turn = 0

    while True:
        try:
            user_message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_message:
            continue
        if user_message in {"/exit", "/quit"}:
            break
        if user_message == "/reset":
            if runtime_dir.exists():
                shutil.rmtree(runtime_dir)
            app = build_memory_graph()
            session_turn = 0
            print("Session reset.")
            continue

        session_turn += 1
        app.agent.ingest_user_message(user_message)
        state = app.agent.retrieve_memory(user_message)
        prompt = build_prompt(user_message, state)
        try:
            assistant_message = responder.generate(prompt)
        except Exception as exc:
            print(f"OpenAI request failed: {exc}")
            continue
        app.agent.commit_turn(user_message, assistant_message)
        snapshot_state = app.agent.retrieve_memory(user_message)
        print(f"[{session_turn}] {assistant_message}")
        print(format_memory_snapshot(snapshot_state))


if __name__ == "__main__":
    main()
