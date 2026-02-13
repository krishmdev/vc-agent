"""RAG over the Sequoia knowledge base (ChromaDB).

Each embedder gets its own collections. An index build writes a new *generation*
(`sequoia_kb__<embedder>__g<timestamp>`), tags it with the embedder_id, and only then swaps the
pointer in `chroma_db/active.json` (write-temp + os.replace). A build that fails halfway is
deleted and the previous generation keeps serving. Queries check that the active collection's
embedder_id equals the running embedder's, so OpenAI and MiniLM vectors are never compared.
"""

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path

import config
from embeddings import Embedder, make_embedder

COLLECTION_PREFIX = "sequoia_kb"
POINTER_FILE = "active.json"


class EmbedderMismatch(RuntimeError):
    pass


class IndexNotBuilt(RuntimeError):
    pass


@dataclass
class Hit:
    text: str
    source: str
    type: str
    url: str | None
    chunk_index: int | None
    score: float

    def as_dict(self) -> dict:
        return asdict(self)


def get_chroma_client(path: Path = config.CHROMA_DIR):
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))


def _pointer_path(db_path: Path) -> Path:
    return db_path / POINTER_FILE


def read_pointer(db_path: Path = config.CHROMA_DIR) -> dict:
    try:
        return json.loads(_pointer_path(db_path).read_text())
    except FileNotFoundError:
        return {}


def _write_pointer(db_path: Path, pointer: dict) -> None:
    db_path.mkdir(parents=True, exist_ok=True)
    tmp = _pointer_path(db_path).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(pointer, indent=2) + "\n")
    os.replace(tmp, _pointer_path(db_path))


def build_generation(
    embedder: Embedder,
    documents: list[str],
    ids: list[str],
    metadatas: list[dict],
    *,
    db_path: Path = config.CHROMA_DIR,
    extra_metadata: dict | None = None,
    batch_size: int = 64,
    progress=print,
) -> str:
    """Embed and index a full corpus into a fresh collection, then make it active."""
    client = get_chroma_client(db_path)
    name = f"{COLLECTION_PREFIX}__{embedder.slug}__g{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    collection = client.create_collection(
        name=name,
        embedding_function=None,
        metadata={
            "embedder_id": embedder.embedder_id,
            "dim": embedder.dim,
            "hnsw:space": "cosine",
            **(extra_metadata or {}),
        },
    )
    try:
        for start in range(0, len(documents), batch_size):
            end = start + batch_size
            vectors = embedder.embed_documents(documents[start:end])
            if any(len(v) != embedder.dim for v in vectors):
                raise EmbedderMismatch(f"{embedder.embedder_id} returned a vector of the wrong size")
            collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
                embeddings=vectors,
            )
            if (start // batch_size + 1) % 20 == 0:
                progress(f"  embedded {min(end, len(documents))}/{len(documents)} chunks")
    except BaseException:
        client.delete_collection(name)
        raise

    pointer = read_pointer(db_path)
    previous = pointer.get(embedder.slug, {}).get("collection")
    pointer[embedder.slug] = {
        "collection": name,
        "embedder_id": embedder.embedder_id,
        "count": collection.count(),
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    _write_pointer(db_path, pointer)
    if previous and previous != name:
        try:
            client.delete_collection(previous)
        except Exception:
            pass  # already gone; the pointer no longer references it either way
    return name


class KnowledgeBase:
    def __init__(self, embedder: Embedder, db_path: Path = config.CHROMA_DIR) -> None:
        self.embedder = embedder
        self.db_path = db_path
        self._collection = None
        self._collection_name = None

    def _active(self):
        entry = read_pointer(self.db_path).get(self.embedder.slug)
        if not entry:
            raise IndexNotBuilt(
                f"no {self.embedder.slug} index in {self.db_path}; run "
                + ("`make index-offline`" if self.embedder.slug.startswith("minilm") else "`make index-live`")
            )
        if entry["collection"] != self._collection_name:
            collection = get_chroma_client(self.db_path).get_collection(entry["collection"])
            tagged = (collection.metadata or {}).get("embedder_id")
            if tagged != self.embedder.embedder_id:
                raise EmbedderMismatch(
                    f"collection {entry['collection']} was built with {tagged}, "
                    f"but the running embedder is {self.embedder.embedder_id}"
                )
            self._collection, self._collection_name = collection, entry["collection"]
        return self._collection

    @property
    def collection_name(self) -> str | None:
        return self._collection_name

    def count(self) -> int:
        return self._active().count()

    def search(self, query: str, top_k: int = 4) -> list[Hit]:
        collection = self._active()
        n = min(top_k, collection.count())
        if n == 0:
            return []
        res = collection.query(
            query_embeddings=[self.embedder.embed_query(query)],
            n_results=n,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            meta = meta or {}
            hits.append(
                Hit(
                    text=doc,
                    source=meta.get("source", "Unknown source"),
                    type=meta.get("type", "unknown"),
                    url=meta.get("url") or None,
                    chunk_index=meta.get("chunk_index"),
                    score=round(1.0 - float(dist), 4),
                )
            )
        return hits


@cache
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase(make_embedder())


def format_hits(hits: list[Hit]) -> list[str]:
    """Hits as text blocks with a source line, the format the agent tools hand to the LLM."""
    out = []
    for h in hits:
        source = h.source.replace(".txt", "").replace("_", " ")
        header = f"[Source: {source}" + (f" | {h.url}" if h.url else "") + "]"
        out.append(f"{header}\n{h.text}")
    return out


def search(query: str, top_k: int = 10) -> list[str]:
    """Search the knowledge base; returns formatted passages with source attribution."""
    try:
        hits = get_knowledge_base().search(query, top_k=top_k)
    except IndexNotBuilt as exc:
        return [f"The knowledge base is empty. {exc}"]
    return format_hits(hits) or ["No relevant information found."]


def get_document_count() -> int:
    return get_knowledge_base().count()
