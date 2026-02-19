"""Long-term memory behind the Mem0 client's interface.

The agent only calls three methods, `add`, `get_all` and `search`, with Mem0's keyword arguments,
and reads Mem0's `{"results": [{"memory": ...}]}` response shape. In live mode those go to
Mem0's AsyncMemoryClient. LocalMemoryStore implements the same three calls on SQLite for
offline mode.

The one real difference: Mem0 runs an LLM over each message to extract facts, while the local
store keeps the founder's own statements verbatim and ignores assistant turns. Search ranks those
statements by MiniLM cosine similarity (the same pinned local embedder as the knowledge base)
plus a small BM25 term, so "pricing" finds "we charge $300 a month".
"""

import array
import asyncio
import math
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Protocol

import config
from textutil import tokens


class MemoryStore(Protocol):
    async def add(self, messages: list[dict[str, str]], user_id: str, **kwargs: Any) -> dict: ...

    async def get_all(self, user_id: str, limit: int = 100, **kwargs: Any) -> dict: ...

    async def search(self, query: str, user_id: str, **kwargs: Any) -> dict: ...


_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    memory TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at REAL NOT NULL,
    embedding BLOB
);
CREATE INDEX IF NOT EXISTS memories_user ON memories(user_id, created_at);
"""


# Minimum MiniLM cosine for a memory to match when no query term overlaps. Short topical queries
# ("pricing", "first customers") score about 0.2-0.4 against a multi-clause founder statement;
# unrelated queries score below 0.
MIN_SIMILARITY = 0.2


class LocalMemoryStore:
    def __init__(self, path: Path | str, embedder=None) -> None:
        self.embedder = embedder
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _row(row: sqlite3.Row, score: float | None = None) -> dict:
        created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(row["created_at"]))
        out = {"id": row["id"], "memory": row["memory"], "user_id": row["user_id"], "created_at": created}
        if score is not None:
            out["score"] = round(score, 4)
        return out

    def _add(self, messages: list[dict[str, str]], user_id: str) -> dict:
        results = []
        with self._connect() as db:
            for msg in messages:
                text = (msg.get("content") or "").strip()
                if msg.get("role", "user") != "user" or not text:
                    continue
                exists = db.execute(
                    "SELECT 1 FROM memories WHERE user_id = ? AND memory = ?", (user_id, text)
                ).fetchone()
                if exists:
                    continue
                mem_id = str(uuid.uuid4())
                vector = None
                if self.embedder is not None:
                    vector = array.array("f", self.embedder.embed_query(text)).tobytes()
                db.execute(
                    "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?)",
                    (mem_id, user_id, text, "user", time.time(), vector),
                )
                results.append({"id": mem_id, "memory": text, "event": "ADD"})
        return {"results": results}

    def _get_all(self, user_id: str, limit: int) -> dict:
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
        return {"results": [self._row(r) for r in rows]}

    def _search(self, query: str, user_id: str, limit: int) -> dict:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM memories WHERE user_id = ?", (user_id,)).fetchall()
        q = set(tokens(query))
        if not rows or not (q or self.embedder):
            return {"results": []}
        qvec = self.embedder.embed_query(query) if self.embedder is not None else None
        docs = [tokens(r["memory"]) for r in rows]
        avg_len = sum(len(d) for d in docs) / len(docs) or 1.0
        df = {t: sum(1 for d in docs if t in d) for t in q}
        k1, b = 1.2, 0.75
        scored = []
        for row, doc in zip(rows, docs):
            score = 0.0
            for t in q:
                tf = doc.count(t)
                if not tf:
                    continue
                idf = math.log(1 + (len(docs) - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * len(doc) / avg_len))
            similarity = 0.0
            if qvec is not None and row["embedding"]:
                mvec = array.array("f", row["embedding"])
                similarity = sum(a * b for a, b in zip(qvec, mvec))  # both unit-normalized
            if score > 0 or similarity >= MIN_SIMILARITY:
                scored.append((similarity + 0.1 * score, row["created_at"], row))
        scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
        return {"results": [self._row(r, s) for s, _, r in scored[:limit]]}

    async def add(self, messages: list[dict[str, str]], user_id: str, **kwargs: Any) -> dict:
        return await asyncio.to_thread(self._add, messages, user_id)

    async def get_all(self, user_id: str, limit: int = 100, **kwargs: Any) -> dict:
        return await asyncio.to_thread(self._get_all, user_id, limit)

    async def search(self, query: str, user_id: str, limit: int = 5, **kwargs: Any) -> dict:
        return await asyncio.to_thread(self._search, query, user_id, limit)


def make_memory_store() -> MemoryStore | None:
    """Offline: SQLite. Live: Mem0 cloud if MEM0_API_KEY is set, otherwise memory is off."""
    if config.OFFLINE or config.MEMORY_BACKEND == "local":
        from embeddings import MiniLMEmbedder

        return LocalMemoryStore(config.MEMORY_DB, embedder=MiniLMEmbedder())
    api_key = config.key("MEM0_API_KEY")
    if not api_key:
        return None
    from mem0 import AsyncMemoryClient

    return AsyncMemoryClient(api_key=api_key)
