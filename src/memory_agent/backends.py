from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def approx_token_count(text: str) -> int:
    return max(1, len(text) // 4)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class ConversationBufferMemory:
    max_messages: int = 12
    messages: list[dict[str, str]] = field(default_factory=list)

    def append(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content, "created_at": utc_now()})
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages :]

    def recent(self) -> list[dict[str, str]]:
        return list(self.messages)

    def trim_to_budget(self, max_messages: int) -> None:
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages :]

    def save_context(self, inputs: dict[str, str], outputs: dict[str, str]) -> None:
        if "input" in inputs:
            self.append("user", inputs["input"])
        if "output" in outputs:
            self.append("assistant", outputs["output"])

    def load_memory_variables(self, _: dict[str, Any] | None = None) -> dict[str, list[dict[str, str]]]:
        return {"history": self.recent()}

    def clear(self) -> None:
        self.messages = []


ShortTermConversationBuffer = ConversationBufferMemory


@dataclass
class JsonProfileMemory:
    path: Path
    facts: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        self.facts = payload.get("facts", {})
        self.provenance = payload.get("provenance", {})

    def save(self) -> None:
        ensure_parent(self.path)
        payload = {"facts": self.facts, "provenance": self.provenance}
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def update(self, key: str, value: str, source: str) -> None:
        self.facts[key] = value
        self.provenance[key] = {"source": source, "updated_at": utc_now()}
        self.save()

    def delete(self, key: str) -> None:
        self.facts.pop(key, None)
        self.provenance.pop(key, None)
        self.save()

    def as_dict(self) -> dict[str, str]:
        return dict(self.facts)


class _FactsProxy:
    def __init__(self, provider: Any):
        self.provider = provider

    def __getitem__(self, key: str) -> str:
        return self.provider.as_dict()[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.provider.as_dict().get(key, default)

    def items(self):
        return self.provider.as_dict().items()

    def __iter__(self):
        return iter(self.provider.as_dict())

    def __contains__(self, key: object) -> bool:
        return key in self.provider.as_dict()


@dataclass
class RedisProfileMemory:
    namespace: str = "memory_agent:profile"
    url: str = "redis://localhost:6379/0"
    fallback: JsonProfileMemory | None = None
    client: Any = field(init=False, default=None)
    available: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        try:
            import redis  # type: ignore

            self.client = redis.from_url(self.url, decode_responses=True)
            self.client.ping()
            self.available = True
        except Exception:
            self.client = None
            self.available = False
            if self.fallback is None:
                self.fallback = JsonProfileMemory(Path("data/profile.json"))

    def update(self, key: str, value: str, source: str) -> None:
        if self.available and self.client is not None:
            self.client.hset(self.namespace, mapping={key: value})
            meta_key = f"{self.namespace}:meta"
            self.client.hset(meta_key, mapping={key: json.dumps({"source": source, "updated_at": utc_now()})})
            return
        assert self.fallback is not None
        self.fallback.update(key, value, source)

    def delete(self, key: str) -> None:
        if self.available and self.client is not None:
            self.client.hdel(self.namespace, key)
            self.client.hdel(f"{self.namespace}:meta", key)
            return
        assert self.fallback is not None
        self.fallback.delete(key)

    def as_dict(self) -> dict[str, str]:
        if self.available and self.client is not None:
            raw = self.client.hgetall(self.namespace)
            return {k: v for k, v in raw.items()}
        assert self.fallback is not None
        return self.fallback.as_dict()

    @property
    def facts(self) -> _FactsProxy:
        return _FactsProxy(self)

    @property
    def provenance(self) -> dict[str, Any]:
        if self.available and self.client is not None:
            meta = self.client.hgetall(f"{self.namespace}:meta")
            return {k: json.loads(v) for k, v in meta.items()}
        assert self.fallback is not None
        return self.fallback.provenance


@dataclass
class JsonEpisodicLog:
    path: Path
    episodes: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        self.episodes = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self.episodes.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def append_episode(self, episode: dict[str, Any]) -> None:
        episode = dict(episode)
        episode.setdefault("created_at", utc_now())
        self.episodes.append(episode)
        ensure_parent(self.path)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(episode, ensure_ascii=False) + "\n")

    def recent(self, limit: int = 5) -> list[dict[str, Any]]:
        return self.episodes[-limit:]


@dataclass
class KeywordSemanticMemory:
    path: Path
    chunks: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        self.chunks = payload.get("chunks", [])

    def save(self) -> None:
        ensure_parent(self.path)
        self.path.write_text(json.dumps({"chunks": self.chunks}, ensure_ascii=False, indent=2), encoding="utf-8")

    def add_chunk(self, chunk_id: str, text: str, tags: list[str] | None = None) -> None:
        self.chunks.append(
            {
                "id": chunk_id,
                "text": text,
                "tags": tags or [],
                "created_at": utc_now(),
            }
        )
        self.save()

    def search(self, query: str, limit: int = 3) -> list[str]:
        query_tokens = set(normalize_text(query))
        scored: list[tuple[int, str]] = []
        for chunk in self.chunks:
            text_tokens = set(normalize_text(chunk["text"])) | set(chunk.get("tags", []))
            score = len(query_tokens & text_tokens)
            if score:
                scored.append((score, chunk["text"]))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [text for _, text in scored[:limit]]


@dataclass
class ChromaSemanticMemory:
    persist_dir: Path
    collection_name: str = "memory_agent_semantic"
    fallback: KeywordSemanticMemory | None = None
    available: bool = field(init=False, default=False)
    client: Any = field(init=False, default=None)
    collection: Any = field(init=False, default=None)

    def __post_init__(self) -> None:
        try:
            import chromadb  # type: ignore
            from chromadb.config import Settings  # type: ignore

            class LocalEmbeddingFunction:
                name = "local_embedding_function"

                def is_legacy(self) -> bool:
                    return False

                def default_space(self) -> str:
                    return "cosine"

                def supported_spaces(self) -> list[str]:
                    return ["cosine"]

                def __call__(self, input: list[str]) -> list[list[float]]:
                    vectors: list[list[float]] = []
                    for text in input:
                        tokens = normalize_text(text)
                        vector = [0.0] * 32
                        for token in tokens:
                            index = sum(ord(ch) for ch in token) % len(vector)
                            vector[index] += 1.0
                        vectors.append(vector)
                    return vectors

            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False),
            )
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=LocalEmbeddingFunction(),
            )
            self.available = True
        except Exception:
            self.client = None
            self.collection = None
            self.available = False
            if self.fallback is None:
                self.fallback = KeywordSemanticMemory(self.persist_dir / "semantic_fallback.json")

    def add_chunk(self, chunk_id: str, text: str, tags: list[str] | None = None) -> None:
        tags = tags or []
        if self.available and self.collection is not None:
            try:
                self.collection.upsert(ids=[chunk_id], documents=[text], metadatas=[{"tags": ",".join(tags)}])
                return
            except Exception:
                self.available = False
        assert self.fallback is not None
        self.fallback.add_chunk(chunk_id, text, tags)

    def search(self, query: str, limit: int = 3) -> list[str]:
        if self.available and self.collection is not None:
            try:
                collection_size = 0
                if hasattr(self.collection, "count"):
                    try:
                        collection_size = int(self.collection.count())
                    except Exception:
                        collection_size = 0
                if collection_size <= 0:
                    return []
                result = self.collection.query(query_texts=[query], n_results=min(limit, collection_size))
                docs = result.get("documents", [[]])
                return list(dict.fromkeys(doc for doc in docs[0] if doc))
            except Exception:
                self.available = False
        assert self.fallback is not None
        return list(dict.fromkeys(self.fallback.search(query, limit=limit)))


@dataclass
class MemoryContextManager:
    max_tokens: int = 800
    profile_tokens: int = 120
    episodic_tokens: int = 220
    semantic_tokens: int = 220
    recent_tokens: int = 240

    def budget_sections(
        self,
        profile: dict[str, str],
        episodes: list[dict[str, Any]],
        semantic_hits: list[str],
        recent_messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        profile_lines = self._profile_lines(profile)
        episode_texts = [
            f"- {ep.get('title', 'episode')}: {ep.get('summary', '')} ({ep.get('outcome', '')})"
            for ep in episodes
        ]
        semantic_lines = [f"- {hit}" for hit in semantic_hits]
        recent_lines = [f"- {msg['role']}: {msg['content']}" for msg in recent_messages]

        profile_text = self._pack_lines(profile_lines, self.profile_tokens)
        episode_text = self._pack_lines(episode_texts, self.episodic_tokens)
        semantic_text = self._pack_lines(semantic_lines, self.semantic_tokens)
        recent_text = self._pack_lines(recent_lines, self.recent_tokens)

        sections = [
            ("recent_text", recent_text, 4),
            ("semantic_text", semantic_text, 3),
            ("episode_text", episode_text, 2),
            ("profile_text", profile_text, 1),
        ]
        total = sum(approx_token_count(text) for _, text, _ in sections)
        if total > self.max_tokens:
            sections = self._apply_priority_eviction(sections)
        total = sum(approx_token_count(text) for _, text, _ in sections)
        section_map = {name: text for name, text, _ in sections}
        return {
            "profile_text": section_map["profile_text"],
            "episode_text": section_map["episode_text"],
            "semantic_text": section_map["semantic_text"],
            "recent_text": section_map["recent_text"],
            "token_estimate": total,
            "context_tokens": {
                "profile": approx_token_count(section_map["profile_text"]),
                "episodic": approx_token_count(section_map["episode_text"]),
                "semantic": approx_token_count(section_map["semantic_text"]),
                "recent": approx_token_count(section_map["recent_text"]),
            },
        }

    def _pack_lines(self, lines: list[str], max_tokens: int) -> str:
        packed: list[str] = []
        budget = max_tokens
        for line in lines:
            line_tokens = approx_token_count(line)
            if line_tokens <= budget:
                packed.append(line)
                budget -= line_tokens
        return "\n".join(packed) or "- không có"

    def _apply_priority_eviction(self, sections: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
        mutable = list(sections)
        for idx, (name, text, priority) in enumerate(mutable):
            if sum(approx_token_count(t) for _, t, _ in mutable) <= self.max_tokens:
                break
            if name == "recent_text" and text != "- không có":
                mutable[idx] = (name, self._truncate_text(text, max(40, self.recent_tokens // 2)), priority)
        if sum(approx_token_count(t) for _, t, _ in mutable) <= self.max_tokens:
            return mutable
        for idx, (name, text, priority) in enumerate(mutable):
            if name == "semantic_text" and text != "- không có":
                mutable[idx] = (name, self._truncate_text(text, max(30, self.semantic_tokens // 2)), priority)
        if sum(approx_token_count(t) for _, t, _ in mutable) <= self.max_tokens:
            return mutable
        for idx, (name, text, priority) in enumerate(mutable):
            if name == "episode_text" and text != "- không có":
                mutable[idx] = (name, self._truncate_text(text, max(30, self.episodic_tokens // 2)), priority)
        if sum(approx_token_count(t) for _, t, _ in mutable) <= self.max_tokens:
            return mutable
        for idx, (name, text, priority) in enumerate(mutable):
            if name == "profile_text" and text != "- không có":
                mutable[idx] = (name, self._truncate_text(text, max(20, self.profile_tokens // 2)), priority)
        return mutable

    def _truncate_text(self, text: str, max_tokens: int) -> str:
        if approx_token_count(text) <= max_tokens:
            return text
        max_chars = max_tokens * 4
        return text[:max_chars].rstrip() + "..."

    def _profile_lines(self, profile: dict[str, str]) -> list[str]:
        lines = [f"- {k}: {v}" for k, v in profile.items()]
        lines.sort()
        return lines or ["- không có"]


@dataclass
class MemoryStore:
    short_term: ConversationBufferMemory = field(default_factory=ConversationBufferMemory)
    profile: Any = None
    episodic: JsonEpisodicLog | None = None
    semantic: Any = None
    context_manager: MemoryContextManager = field(default_factory=MemoryContextManager)

    def __post_init__(self) -> None:
        data_dir = Path(os.getenv("MEMORY_DATA_DIR", "data"))
        profile_json = JsonProfileMemory(data_dir / "profile.json")
        self.profile = RedisProfileMemory(fallback=profile_json)
        self.episodic = JsonEpisodicLog(data_dir / "episodic.jsonl")
        self.semantic = ChromaSemanticMemory(data_dir / "chroma", fallback=KeywordSemanticMemory(data_dir / "semantic.json"))

    def retrieve(self, query: str, budget: int = 8) -> dict[str, Any]:
        return self.retrieve_by_route(query, route="all", budget=budget)

    def retrieve_by_route(self, query: str, route: str = "all", budget: int = 8) -> dict[str, Any]:
        recent = self.short_term.recent()[-budget:]
        profile = self.profile.as_dict()
        episodes = self.episodic.recent(limit=3) if route in {"all", "episodic"} else []
        semantic_hits = self.semantic.search(query, limit=3) if route in {"all", "semantic"} else []
        selected_types = ["recent"]
        if route in {"all", "profile"}:
            selected_types.append("profile")
        if route in {"all", "episodic"}:
            selected_types.append("episodic")
        if route in {"all", "semantic"}:
            selected_types.append("semantic")
        sections = self.context_manager.budget_sections(
            profile if route in {"all", "profile"} else {},
            episodes,
            semantic_hits,
            recent,
        )
        return {
            "recent_messages": recent,
            "user_profile": profile if route in {"all", "profile"} else {},
            "episodes": episodes,
            "semantic_hits": semantic_hits,
            "memory_budget": budget,
            "memory_scope": route,
            "selected_memory_types": selected_types,
            "context_sections": sections,
        }

    def append_episode(self, episode: dict[str, Any]) -> None:
        assert self.episodic is not None
        self.episodic.append_episode(episode)
