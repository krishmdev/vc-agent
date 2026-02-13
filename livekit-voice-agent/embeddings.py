"""Embedders for the knowledge base.

Every embedder carries an embedder_id of the form provider/model/revision/dim/preprocessing-hash.
Collections are tagged with it, and a query against a collection built by a different embedder
is refused, so vectors from different models never meet.
"""

import hashlib
import os
import time
from functools import cached_property
from typing import Protocol

import numpy as np

import config


def _prep_hash(description: str) -> str:
    return "p" + hashlib.sha256(description.encode()).hexdigest()[:8]


class Embedder(Protocol):
    embedder_id: str
    dim: int
    slug: str  # short, collection-name-safe identifier for the embedder family

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class MiniLMEmbedder:
    """all-MiniLM-L6-v2 through its ONNX export: mean pooling over tokens, then L2 normalize.

    That matches the sentence-transformers pipeline for this model (Transformer -> Pooling(mean)
    -> Normalize) without pulling in torch.
    """

    slug = "minilm-l6-v2"
    dim = 384
    max_tokens = 256  # sentence_bert_config.json max_seq_length
    batch_size = 32

    def __init__(self) -> None:
        from model_store import MINILM_REPO, lock_entry, load_lock

        self.revision = lock_entry(MINILM_REPO, load_lock())["revision"]
        prep = f"tokens<={self.max_tokens};mean-pool;l2-normalize"
        self.embedder_id = f"local-onnx/all-MiniLM-L6-v2/{self.revision[:12]}/{self.dim}/{_prep_hash(prep)}"

    @cached_property
    def _session(self):
        import onnxruntime as ort

        from model_store import verified_model_dir

        root = verified_model_dir()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = int(os.environ.get("KB_EMBED_THREADS", "0"))
        return ort.InferenceSession(str(root / "onnx" / "model.onnx"), opts, providers=["CPUExecutionProvider"])

    @cached_property
    def _tokenizer(self):
        from tokenizers import Tokenizer

        from model_store import verified_model_dir

        tok = Tokenizer.from_file(str(verified_model_dir() / "tokenizer.json"))
        tok.enable_truncation(max_length=self.max_tokens)
        tok.enable_padding(pad_id=0, pad_token="[PAD]")
        return tok

    def _embed(self, texts: list[str]) -> np.ndarray:
        out = []
        input_names = {i.name for i in self._session.get_inputs()}
        for start in range(0, len(texts), self.batch_size):
            batch = self._tokenizer.encode_batch(texts[start : start + self.batch_size])
            ids = np.array([e.ids for e in batch], dtype=np.int64)
            mask = np.array([e.attention_mask for e in batch], dtype=np.int64)
            feeds = {"input_ids": ids, "attention_mask": mask}
            if "token_type_ids" in input_names:
                feeds["token_type_ids"] = np.array([e.type_ids for e in batch], dtype=np.int64)
            hidden = self._session.run(None, feeds)[0]
            m = mask[..., None].astype(np.float32)
            pooled = (hidden * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
            pooled /= np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
            out.append(pooled.astype(np.float32))
        return np.vstack(out) if out else np.zeros((0, self.dim), dtype=np.float32)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text])[0].tolist()


class OpenAIEmbedder:
    slug = "openai-te3-small"
    dim = 1536
    model = "text-embedding-3-small"
    batch_size = 100

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or config.key("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI knowledge-base collection")
        self.embedder_id = f"openai/{self.model}/-/{self.dim}/{_prep_hash('raw-text')}"

    @cached_property
    def _client(self):
        from openai import OpenAI

        return OpenAI(api_key=self.api_key, max_retries=5)

    def _create(self, texts: list[str]) -> list[list[float]]:
        for attempt in range(5):
            try:
                resp = self._client.embeddings.create(model=self.model, input=texts)
                return [d.embedding for d in resp.data]
            except Exception as exc:  # the SDK retries 429s itself; this covers long rate-limit windows
                rate_limited = "429" in str(exc) or "rate" in str(exc).lower()
                if not rate_limited or attempt == 4:
                    raise
                time.sleep(2**attempt)
        raise RuntimeError("unreachable")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            vectors.extend(self._create(texts[start : start + self.batch_size]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._create([text])[0]


def make_embedder(kind: str | None = None) -> Embedder:
    kind = (kind or config.KB_EMBEDDER).lower()
    if config.OFFLINE and kind != "local":
        raise RuntimeError("offline mode only supports the local embedder")
    if kind == "local":
        return MiniLMEmbedder()
    if kind == "openai":
        return OpenAIEmbedder()
    raise ValueError(f"unknown embedder {kind!r} (expected 'local' or 'openai')")
