# Multi-Memory Agent for Lab #17

This repository contains a memory-aware agent for the VinUni Lab #17 rubric:

- short-term conversation buffer
- long-term profile memory
- JSON episodic log
- semantic memory with Chroma fallback
- LangGraph-style state/router flow
- conflict-aware profile updates
- benchmark report for 10 multi-turn conversations

## What is included

- `src/memory_agent/`: agent, memory backends, graph, prompt, and state
- `examples/demo.py`: runnable transcript demo
- `scripts/generate_benchmark_report.py`: generates `reports/BENCHMARK_REPORT.md`
- `BENCHMARK.md`: 10 scenario benchmark write-up
- `REFLECTION.md`: privacy and limitation reflection
- `reports/`: generated benchmark report
- `data/`: local persistence for profile, episodic, and semantic storage
- `tests/`: rubric-focused regression tests

## Setup

```bash
python3 -m pip install -r requirements.txt
```

If you want the optional compiled LangGraph runtime:

```bash
python3 -m pip install -e ".[langgraph]"
```

If you want Redis or Chroma extras as well:

```bash
python3 -m pip install -e ".[redis,semantic]"
```

## Run

```bash
python3 examples/demo.py
python3 scripts/chat_cli.py
python3 scripts/generate_benchmark_report.py
python3 -m pytest
```

## OpenAI CLI Chat

Create a `.env` file at the repo root or export env vars directly:

```bash
OPENAI_API_KEY="..."
OPENAI_MODEL="gpt-4.1-mini"
OPENAI_MAX_OUTPUT_TOKENS="256"
```

Then run:

```bash
python3 scripts/chat_cli.py
```

The CLI prints the assistant reply plus a memory snapshot after each turn so you can see what the agent retained.

## Outputs

- `data/profile.json`: long-term profile fallback storage
- `data/episodic.jsonl`: episodic memory log
- `data/semantic.json`: fallback semantic store
- `data/chroma/`: optional Chroma persistence
- `reports/BENCHMARK_REPORT.md`: generated metrics report
- `scripts/chat_cli.py`: interactive terminal chat for manual testing

## Implementation notes

- The agent prefers Redis and Chroma when available.
- If Redis or Chroma are not available, the code falls back to local JSON and keyword search so the project still runs offline.
- The graph entrypoint works with LangGraph if installed, or with the built-in fallback runtime otherwise.
