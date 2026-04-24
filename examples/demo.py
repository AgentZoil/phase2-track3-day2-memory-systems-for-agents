from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from memory_agent import build_memory_graph


def main() -> None:
    app = build_memory_graph()
    turns = [
        "Tôi tên là Linh.",
        "Tôi dị ứng sữa bò.",
        "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.",
        "Tên tôi là gì?",
        "Tôi dị ứng gì?",
    ]
    state = {"messages": []}
    for turn in turns:
        state = app.invoke({"messages": [{"role": "user", "content": turn}]})
        print(f"USER: {turn}")
        print(f"ASSISTANT: {state.get('assistant_message', '')}")


if __name__ == "__main__":
    main()
