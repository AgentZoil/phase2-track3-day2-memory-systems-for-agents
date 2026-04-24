from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from memory_agent import build_memory_graph
from memory_agent.agent import MultiMemoryAgent


@dataclass
class Session:
    graph: Any


SESSIONS: dict[str, Session] = {}


def get_session(session_id: str | None = None) -> tuple[str, Session]:
    if not session_id:
        session_id = str(uuid4())
    session = SESSIONS.get(session_id)
    if session is None:
        session = Session(graph=build_memory_graph(MultiMemoryAgent()))
        SESSIONS[session_id] = session
    return session_id, session


class MemoryAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send_json(200, {"ok": True})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/invoke":
            self._send_json(404, {"error": "not_found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(400, {"error": f"invalid_json: {exc}"})
            return

        message = str(payload.get("message", "")).strip()
        if not message:
            self._send_json(400, {"error": "message is required"})
            return

        session_id, session = get_session(payload.get("session_id"))
        state = session.graph.invoke({"messages": [{"role": "user", "content": message}]})

        self._send_json(
            200,
            {
                "session_id": session_id,
                "assistant_message": state.get("assistant_message", ""),
                "prompt": state.get("prompt", ""),
                "memory": {
                    "profile": state.get("user_profile", {}),
                    "episodes": state.get("episodes", []),
                    "semantic_hits": state.get("semantic_hits", []),
                    "recent_messages": state.get("recent_messages", []),
                },
            },
        )

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    host = os.getenv("MEMORY_API_HOST", "127.0.0.1")
    port = int(os.getenv("MEMORY_API_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), MemoryAPIHandler)
    print(f"Serving memory API at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
