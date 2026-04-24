from __future__ import annotations

import sys
import os
import shutil
from dataclasses import dataclass
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from memory_agent import build_memory_graph
from memory_agent.agent import MultiMemoryAgent
from memory_agent.backends import approx_token_count


@dataclass
class Scenario:
    name: str
    turns: list[str]
    expected_keywords: list[str]
    preload_semantic: list[tuple[str, str, list[str]]]
    metric_type: str


SCENARIOS = [
    Scenario(
        name="Recall user name",
        turns=["Chào, tôi tên là Linh.", "Tôi thích trà sữa.", "Tên tôi là gì?"],
        expected_keywords=["Linh"],
        preload_semantic=[],
        metric_type="profile",
    ),
    Scenario(
        name="Recall user city",
        turns=["Tôi sống ở Hà Nội.", "Tôi học buổi tối.", "Tôi sống ở đâu?"],
        expected_keywords=["Hanoi", "Hà Nội"],
        preload_semantic=[],
        metric_type="profile",
    ),
    Scenario(
        name="Allergy conflict update",
        turns=["Tôi dị ứng sữa bò.", "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.", "Tôi dị ứng gì?"],
        expected_keywords=["đậu nành"],
        preload_semantic=[],
        metric_type="profile",
    ),
    Scenario(
        name="Preference change",
        turns=["Tôi thích cà phê đen.", "À nhầm, tôi thích trà nóng hơn cà phê.", "Tôi thích gì?"],
        expected_keywords=["trà nóng"],
        preload_semantic=[],
        metric_type="profile",
    ),
    Scenario(
        name="Episode recall",
        turns=["Mình đang debug lỗi deploy.", "Task done: fixed the deployment issue.", "Lần trước tôi đã làm xong gì?"],
        expected_keywords=["deployment issue"],
        preload_semantic=[],
        metric_type="episodic",
    ),
    Scenario(
        name="Debug lesson recall",
        turns=[
            "Tôi vừa học được rằng service name trong Docker phải khớp compose file.",
            "Task completed: hiểu nguyên nhân lỗi container.",
            "Bài học debug trước đó là gì?",
        ],
        expected_keywords=["container"],
        preload_semantic=[],
        metric_type="episodic",
    ),
    Scenario(
        name="Semantic FAQ retrieval",
        turns=["I need a reminder about docker service resolution.", "What should I check for docker service resolution?"],
        expected_keywords=["docker compose service name"],
        preload_semantic=[
            ("faq-1", "Use docker compose service name when the container cannot be resolved.", ["docker", "compose"]),
        ],
        metric_type="semantic",
    ),
    Scenario(
        name="Trim budget",
        turns=[
            "Tôi tên là Minh.",
            "Tôi sống ở Đà Nẵng.",
            "Tôi thích học buổi sáng.",
            "Tôi đang làm một chuỗi 10 lượt để kiểm tra trim.",
            "Tôi vừa nhắc lại rất nhiều điều.",
            "Tên tôi là gì và tôi sống ở đâu?",
        ],
        expected_keywords=["Minh", "Đà Nẵng"],
        preload_semantic=[],
        metric_type="budget",
    ),
    Scenario(
        name="Multiple profile facts",
        turns=["Tôi tên là An.", "Tôi sống ở Huế.", "Tôi thích trà.", "Cho tôi nhắc lại tên, nơi ở, và sở thích của tôi."],
        expected_keywords=["An", "Huế", "trà"],
        preload_semantic=[],
        metric_type="profile",
    ),
    Scenario(
        name="Overwrite stale fact",
        turns=["Tôi dị ứng sữa bò.", "Tôi đã đổi chế độ ăn.", "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.", "Sau khi sửa, tôi dị ứng gì?"],
        expected_keywords=["đậu nành"],
        preload_semantic=[],
        metric_type="profile",
    ),
]


def stateless_response(user_message: str) -> str:
    lower = user_message.lower()
    if "tên" in lower:
        return "Mình chưa biết tên bạn."
    if "dị ứng" in lower:
        return "Mình chưa biết bạn dị ứng gì."
    if "ở đâu" in lower:
        return "Mình chưa biết bạn sống ở đâu."
    if "docker" in lower or "faq" in lower:
        return "Mình chưa có ghi chú liên quan."
    return "Mình chưa có đủ ngữ cảnh."


def overlap_score(text: str, keywords: list[str]) -> float:
    lower = text.lower()
    matches = sum(1 for keyword in keywords if keyword.lower() in lower)
    return matches / max(1, len(keywords))


def evaluate_scenario(index: int, scenario: Scenario) -> dict[str, object]:
    runtime_dir = ROOT / "data" / "benchmark_runtime" / f"scenario_{index:02d}"
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    os.environ["MEMORY_DATA_DIR"] = str(runtime_dir)

    graph = build_memory_graph(MultiMemoryAgent())
    if scenario.preload_semantic:
        for chunk_id, text, tags in scenario.preload_semantic:
            graph.agent.store.semantic.add_chunk(chunk_id, text, tags)

    no_memory_answer = stateless_response(scenario.turns[-1])
    state: dict[str, object] = {}
    with_memory_answer = ""
    prompt_tokens = 0
    response_tokens = 0
    memory_tokens = 0
    context_utilization = 0.0

    for turn in scenario.turns:
        state = graph.invoke({"messages": [{"role": "user", "content": turn}]})
        with_memory_answer = str(state.get("assistant_message", ""))
        prompt_tokens = approx_token_count(str(state.get("prompt", "")))
        response_tokens = approx_token_count(with_memory_answer)
        context_tokens = state.get("context_sections", {}).get("context_tokens", {})
        memory_tokens = sum(int(v) for v in context_tokens.values()) if context_tokens else 0
        context_utilization = round(memory_tokens / max(1, prompt_tokens), 4)

    return {
        "scenario": scenario.name,
        "type": scenario.metric_type,
        "no_memory": no_memory_answer,
        "with_memory": with_memory_answer,
        "relevance": overlap_score(with_memory_answer, scenario.expected_keywords),
        "memory_hit": 1 if overlap_score(with_memory_answer, scenario.expected_keywords) > 0 else 0,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "memory_tokens": memory_tokens,
        "context_utilization": context_utilization,
        "token_efficiency": round(overlap_score(with_memory_answer, scenario.expected_keywords) / max(1, prompt_tokens + response_tokens), 4),
    }


def render_report(rows: list[dict[str, object]]) -> str:
    avg_relevance = sum(float(row["relevance"]) for row in rows) / len(rows)
    avg_hit_rate = sum(int(row["memory_hit"]) for row in rows) / len(rows)
    avg_prompt_tokens = sum(int(row["prompt_tokens"]) for row in rows) / len(rows)
    avg_response_tokens = sum(int(row["response_tokens"]) for row in rows) / len(rows)
    avg_memory_tokens = sum(int(row["memory_tokens"]) for row in rows) / len(rows)
    avg_context_utilization = sum(float(row["context_utilization"]) for row in rows) / len(rows)
    avg_efficiency = sum(float(row["token_efficiency"]) for row in rows) / len(rows)

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["type"])].append(row)

    category_lines = [
        "| Type | Scenarios | Avg relevance | Hit rate |",
        "|------|-----------|---------------|----------|",
    ]
    for metric_type in sorted(grouped):
        group = grouped[metric_type]
        category_lines.append(
            f"| {metric_type} | {len(group)} | {sum(float(row['relevance']) for row in group) / len(group):.2f} | "
            f"{sum(int(row['memory_hit']) for row in group) / len(group):.2f} |"
        )

    lines = [
        "# Benchmark Report",
        "",
        "## Summary",
        "",
        f"- Average response relevance: {avg_relevance:.2f}",
        f"- Memory hit rate: {avg_hit_rate:.2f}",
        f"- Average prompt tokens: {avg_prompt_tokens:.1f}",
        f"- Average response tokens: {avg_response_tokens:.1f}",
        f"- Average memory tokens: {avg_memory_tokens:.1f}",
        f"- Average context utilization: {avg_context_utilization:.2f}",
        f"- Average token efficiency: {avg_efficiency:.4f}",
        f"- Total scenarios: {len(rows)}",
        f"- Fully successful scenarios: {sum(int(row['memory_hit']) for row in rows)}",
        "",
        "## Scenario Table",
        "",
        "| # | Scenario | Type | No-memory | With-memory | Relevance | Hit | Prompt tok | Mem tok | Context util | Response tok | Efficiency |",
        "|---|----------|------|-----------|-------------|-----------|-----|------------|---------|--------------|--------------|------------|",
    ]
    for idx, row in enumerate(rows, start=1):
        lines.append(
            f"| {idx} | {row['scenario']} | {row['type']} | {row['no_memory']} | {row['with_memory']} | "
            f"{row['relevance']:.2f} | {row['memory_hit']} | {row['prompt_tokens']} | {row['memory_tokens']} | {row['context_utilization']:.2f} | {row['response_tokens']} | {row['token_efficiency']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Coverage By Type",
            "",
            *category_lines,
            "",
            "## Memory Hit Analysis",
            "",
            "- Profile scenarios should hit on stable facts like name, location, allergy, and preference.",
            "- Episodic scenarios should hit on completed tasks or earlier lessons.",
            "- Semantic scenarios should hit on the FAQ-like chunk loaded into semantic memory.",
            "- Budget scenario should show that short-term memory trims while profile facts remain retrievable.",
            "",
            "## Token Budget Breakdown",
            "",
            "- Prompt tokens are estimated from the composed prompt after memory injection.",
            "- Memory tokens count profile, episodic, semantic, and recent sections before the final prompt is formed.",
            "- Context utilization is memory tokens divided by the prompt token estimate.",
            "- Response tokens are estimated from the final assistant message.",
            "- Token efficiency is defined as relevance divided by total estimated tokens.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    runtime_dir = ROOT / "data" / "benchmark_runtime"
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    rows = [evaluate_scenario(index, scenario) for index, scenario in enumerate(SCENARIOS, start=1)]
    report = render_report(rows)
    out = ROOT / "reports" / "BENCHMARK_REPORT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
