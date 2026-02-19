"""Client for the Sequoia knowledge base, served over HTTP by livekit-voice-agent/server.py.

The voice-agent package owns the Chroma collections and the embedder; its server.py and the
LiveKit worker (agent.py) both read them in-process. The research agent never loads an
embedding model or touches Chroma. Which collection answers (OpenAI embeddings in live mode,
local MiniLM offline) is decided by the voice-agent server's mode.
"""

from dataclasses import dataclass

import httpx


class KnowledgeBaseUnavailable(RuntimeError):
    pass


@dataclass
class Passage:
    text: str
    source: str
    type: str
    url: str | None
    score: float | None


class KnowledgeBaseClient:
    def __init__(self, base_url: str, *, timeout: float = 20.0, transport=None) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)
        self.embedder_id: str | None = None

    async def search(self, query: str, top_k: int = 4) -> list[Passage]:
        try:
            resp = await self._client.post("/kb/search", json={"query": query, "top_k": top_k})
        except httpx.HTTPError as exc:
            raise KnowledgeBaseUnavailable(f"knowledge base unreachable: {exc}") from exc
        if resp.status_code != 200:
            raise KnowledgeBaseUnavailable(f"knowledge base returned {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        self.embedder_id = data.get("embedder_id")
        return [
            Passage(
                text=r["text"],
                source=r["source"],
                type=r.get("type", "unknown"),
                url=r.get("url"),
                score=r.get("score"),
            )
            for r in data.get("results", [])
        ]

    async def aclose(self) -> None:
        await self._client.aclose()
