"""Index generations, embedder tagging, and failure handling, with toy embedders."""

import numpy as np
import pytest

import rag


class ToyEmbedder:
    def __init__(self, slug="toy", dim=8, embedder_id=None, fail_after=None):
        self.slug = slug
        self.dim = dim
        self.embedder_id = embedder_id or f"test/{slug}/-/{dim}/p0"
        self.fail_after = fail_after
        self.embedded = 0

    def _vec(self, text):
        rng = np.random.default_rng(sum(map(ord, text.split()[0].lower())))
        v = rng.normal(size=self.dim)
        return (v / np.linalg.norm(v)).tolist()

    def embed_documents(self, texts):
        if self.fail_after is not None and self.embedded + len(texts) > self.fail_after:
            raise RuntimeError("provider down")
        self.embedded += len(texts)
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


def corpus(n=20, tag="doc"):
    docs = [f"{'airbnb' if i % 2 else 'stripe'} {tag} passage {i}" for i in range(n)]
    ids = [f"{tag}-{i}" for i in range(n)]
    metas = [{"source": f"Source {i}", "type": "transcript", "chunk_index": i} for i in range(n)]
    return docs, ids, metas


def test_build_and_search_tags_embedder(tmp_path):
    emb = ToyEmbedder()
    name = rag.build_generation(emb, *corpus(), db_path=tmp_path, batch_size=5, progress=lambda *_: None)
    pointer = rag.read_pointer(tmp_path)
    assert pointer["toy"]["collection"] == name
    assert pointer["toy"]["embedder_id"] == emb.embedder_id

    kb = rag.KnowledgeBase(emb, db_path=tmp_path)
    hits = kb.search("airbnb story", top_k=3)
    assert len(hits) == 3 and all(h.text.startswith("airbnb") for h in hits)


def test_query_with_a_different_embedder_is_refused(tmp_path):
    rag.build_generation(ToyEmbedder(), *corpus(), db_path=tmp_path, progress=lambda *_: None)
    impostor = ToyEmbedder(embedder_id="test/toy/-/8/p-other")  # same family slug, different model
    with pytest.raises(rag.EmbedderMismatch):
        rag.KnowledgeBase(impostor, db_path=tmp_path).search("airbnb")


def test_provider_failure_mid_build_keeps_previous_generation(tmp_path):
    good = ToyEmbedder()
    first = rag.build_generation(good, *corpus(tag="old"), db_path=tmp_path, batch_size=5, progress=lambda *_: None)

    # Fails after 10 of 20 documents were already embedded and written.
    flaky = ToyEmbedder(fail_after=10)
    with pytest.raises(RuntimeError, match="provider down"):
        rag.build_generation(flaky, *corpus(tag="new"), db_path=tmp_path, batch_size=5, progress=lambda *_: None)

    assert rag.read_pointer(tmp_path)["toy"]["collection"] == first
    client = rag.get_chroma_client(tmp_path)
    assert [c.name for c in client.list_collections()] == [first]  # partial generation removed
    hits = rag.KnowledgeBase(good, db_path=tmp_path).search("airbnb", top_k=20)
    assert len(hits) == 20 and all(" old " in h.text for h in hits)


def test_wrong_dimension_aborts_build(tmp_path):
    class Short(ToyEmbedder):
        def embed_documents(self, texts):
            return [v[:4] for v in super().embed_documents(texts)]

    with pytest.raises(rag.EmbedderMismatch):
        rag.build_generation(Short(), *corpus(), db_path=tmp_path, progress=lambda *_: None)
    assert rag.read_pointer(tmp_path) == {}


def test_embedder_families_live_side_by_side(tmp_path):
    a, b = ToyEmbedder(slug="toy-a", dim=8), ToyEmbedder(slug="toy-b", dim=16)
    rag.build_generation(a, *corpus(), db_path=tmp_path, progress=lambda *_: None)
    rag.build_generation(b, *corpus(), db_path=tmp_path, progress=lambda *_: None)
    assert rag.KnowledgeBase(a, db_path=tmp_path).search("stripe")[0].text.startswith("stripe")
    assert rag.KnowledgeBase(b, db_path=tmp_path).search("stripe")[0].text.startswith("stripe")


def test_missing_index_says_how_to_build(tmp_path):
    with pytest.raises(rag.IndexNotBuilt, match="make index"):
        rag.KnowledgeBase(ToyEmbedder(slug="minilm-l6-v2"), db_path=tmp_path).search("x")
