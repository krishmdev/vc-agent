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
