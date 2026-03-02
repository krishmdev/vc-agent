import pytest

from memory import LocalMemoryStore


@pytest.fixture
def store(tmp_path):
    return LocalMemoryStore(tmp_path / "mem.sqlite3")


async def test_add_get_all_and_search_use_mem0_shapes(store):
    await store.add([{"role": "user", "content": "We charge clinics $300 a month per location."}], user_id="u1")
    await store.add([{"role": "user", "content": "Our first customers are independent vet clinics in Ohio."}], user_id="u1")
    await store.add([{"role": "user", "content": "Something for another founder."}], user_id="u2")

    everything = await store.get_all(user_id="u1", limit=10)
    assert [m["memory"] for m in everything["results"]][0].startswith("Our first customers")
    assert len(everything["results"]) == 2

    found = await store.search("what is our pricing per month", user_id="u1", filters={"user_id": "u1"})
    assert found["results"][0]["memory"] == "We charge clinics $300 a month per location."
    assert all(r["user_id"] == "u1" for r in found["results"])


async def test_assistant_turns_and_duplicates_are_not_memories(store):
    await store.add([{"role": "assistant", "content": "Tell me about your market."}], user_id="u")
    await store.add([{"role": "user", "content": "We sell to dentists."}], user_id="u")
    again = await store.add([{"role": "user", "content": "We sell to dentists."}], user_id="u")
    assert again == {"results": []}
    assert [m["memory"] for m in (await store.get_all(user_id="u"))["results"]] == ["We sell to dentists."]


async def test_search_without_overlap_returns_nothing(store):
    await store.add([{"role": "user", "content": "We sell to dentists."}], user_id="u")
    assert (await store.search("quantum cryptography", user_id="u"))["results"] == []


async def test_persists_across_instances(tmp_path):
    path = tmp_path / "mem.sqlite3"
    await LocalMemoryStore(path).add([{"role": "user", "content": "Pricing is usage based."}], user_id="u")
    assert (await LocalMemoryStore(path).get_all(user_id="u"))["results"][0]["memory"] == "Pricing is usage based."


async def test_semantic_search_matches_without_shared_words(tmp_path):
    from embeddings import MiniLMEmbedder

    store = LocalMemoryStore(tmp_path / "sem.sqlite3", embedder=MiniLMEmbedder())
    await store.add([{"role": "user", "content": "We plan to charge each clinic $300 a month."}], user_id="u")
    await store.add([{"role": "user", "content": "My cofounder used to run a dog shelter."}], user_id="u")
    found = await store.search("pricing", user_id="u")
    assert found["results"][0]["memory"] == "We plan to charge each clinic $300 a month."
    assert (await store.search("quantum cryptography research", user_id="u"))["results"] == []


class FixedEmbedder:
    """Every text maps to the same unit vector, so any stored vector with this id matches."""

    def __init__(self, embedder_id, dim):
        self.embedder_id, self.dim = embedder_id, dim

    def embed_query(self, text):
        return [1.0] + [0.0] * (self.dim - 1)


async def test_vectors_from_another_embedder_are_not_compared(tmp_path):
    path = tmp_path / "mixed.sqlite3"
    await LocalMemoryStore(path, embedder=FixedEmbedder("a/model/-/4/p", 4)).add(
        [{"role": "user", "content": "We sell to dentists."}], user_id="u"
    )
    same = LocalMemoryStore(path, embedder=FixedEmbedder("a/model/-/4/p", 4))
    assert (await same.search("zebra", user_id="u"))["results"]  # matched by vector alone
    other = LocalMemoryStore(path, embedder=FixedEmbedder("b/model/-/8/p", 8))
    assert (await other.search("zebra", user_id="u"))["results"] == []
    assert (await other.search("dentists", user_id="u"))["results"]  # lexical still works


async def test_an_untagged_older_store_is_migrated(tmp_path):
    import sqlite3

    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE memories (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, memory TEXT NOT NULL, role TEXT NOT NULL, created_at REAL NOT NULL, embedding BLOB)")
    db.execute("INSERT INTO memories VALUES ('1', 'u', 'We sell to dentists.', 'user', 0, NULL)")
    db.commit()
    db.close()
    store = LocalMemoryStore(path, embedder=FixedEmbedder("a/model/-/4/p", 4))
    assert (await store.search("dentists", user_id="u"))["results"][0]["memory"] == "We sell to dentists."
