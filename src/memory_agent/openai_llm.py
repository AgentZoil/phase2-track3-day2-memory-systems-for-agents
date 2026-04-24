from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _extract_output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text).strip()

    output = getattr(response, "output", None) or []
    chunks: list[str] = []
    for item in output:
        content = getattr(item, "content", None) or []
        for part in content:
            part_text = getattr(part, "text", None)
            if part_text:
                chunks.append(str(part_text))
    return "".join(chunks).strip()


def _load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class OpenAIResponder:
    model: str = "gpt-4.1-mini"
    instructions: str = (
        "Bạn là một trợ lý hội thoại ngắn gọn, tự nhiên, trả lời bằng ngôn ngữ người dùng. "
        "Dựa trên bộ nhớ đã được cung cấp để trả lời chính xác, không lặp lại các nhãn section nội bộ."
    )

    def __post_init__(self) -> None:
        _load_dotenv()

        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover - import guard
            raise RuntimeError(
                "OpenAI SDK is not installed. Run `python3 -m pip install -r requirements.txt` first."
            ) from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set.")

        self.client = OpenAI()

    def generate(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            instructions=self.instructions,
            input=prompt,
            max_output_tokens=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "256")),
        )
        text = _extract_output_text(response)
        return text or "(no response)"
