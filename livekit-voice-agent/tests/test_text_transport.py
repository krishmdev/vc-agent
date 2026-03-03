"""The text transport runs the real Assistant, tools and AgentSession with ScriptedLLM."""

import pytest
from fastapi.testclient import TestClient

import config
import mentor
import rag
import server

AIRBNB = (
    "[From: Airbnb ft Brian Chesky]\nThe founders went door to door in New York to meet their first hosts. "
    "They photographed the apartments themselves because the listings looked bad and nobody booked them."
)
STRIPE = "[From: Stripe]\nThe team installed the product for early customers by hand, on the spot."


class StubKB:
    embedder = type("E", (), {"embedder_id": "stub/kb/-/0/p0"})()
    collection_name = "stub"

    def count(self):
        return 2

    def search(self, query, top_k=4):
        hits = [
            rag.Hit(AIRBNB, "Airbnb ft Brian Chesky", "transcript", None, 0, 0.9),
            rag.Hit(STRIPE, "Stripe story", "website", "https://sequoiacap.com/article/stripe", 0, 0.5),
        ]
        return hits[:top_k]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MEMORY_DB", tmp_path / "memory.sqlite3")
    monkeypatch.setattr(rag, "get_knowledge_base", lambda: StubKB())
    mentor.memory_store.cache_clear()
    with TestClient(server.app, base_url="http://127.0.0.1") as c:
        yield c
    mentor.memory_store.cache_clear()


def test_mentor_turn_cites_the_knowledge_base(client):
    with client.websocket_connect("ws://127.0.0.1/ws/chat?mode=mentor&idea=Vet%20clinic%20software") as ws:
        greeting = ws.receive_json()
        assert greeting["type"] == "agent_message" and "Interesting space" in greeting["text"]

        ws.send_json({"type": "user_message", "text": "How do I get my first customers to trust a new product?"})
        reply = ws.receive_json()
        assert [t["name"] for t in reply["tools"]] == ["search_knowledge_base"]
        assert reply["citations"][0]["source"] == "Airbnb ft Brian Chesky"
        assert "Airbnb ft Brian Chesky" in reply["text"]
        assert '.".' not in reply["text"] and ".." not in reply["text"]
        assert reply["text"].rstrip().endswith("?")  # a follow-up question from the persona prompt


def test_memory_is_stored_and_recalled_across_conversations(client):
    with client.websocket_connect("ws://127.0.0.1/ws/chat?mode=mentor") as ws:
        ws.receive_json()
        ws.send_json({"type": "user_message", "text": "We plan to charge each clinic $300 a month for the software."})
        ws.receive_json()

    stored = client.get("/memories").json()["memories"]
    assert [m["memory"] for m in stored] == ["We plan to charge each clinic $300 a month for the software."]

    with client.websocket_connect("ws://127.0.0.1/ws/chat?mode=mentor") as ws:
        ws.receive_json()
        ws.send_json({"type": "user_message", "text": "What did I tell you about pricing per month?"})
        reply = ws.receive_json()
        assert {t["name"] for t in reply["tools"]} == {"search_knowledge_base", "recall_memory"}
        assert reply["memories"] == ["We plan to charge each clinic $300 a month for the software."]
        assert "$300 a month" in reply["text"]

    # The recall question itself is not written back as a memory.
    assert len(client.get("/memories").json()["memories"]) == 1


def test_vc_report_is_built_from_the_transcript(client, monkeypatch):
    posted = []

    async def fake_post(self):
        return None

    with client.websocket_connect("ws://127.0.0.1/ws/chat?mode=vc&idea=Vet%20software") as ws:
        assert "Pitch me" in ws.receive_json()["text"]
        ws.send_json({"type": "user_message", "text": "Clinics lose hours every week reconciling insurance claims by hand. We charge $300 a month."})
        ws.receive_json()
        ws.send_json({"type": "generate_report"})
        report = ws.receive_json()
    assert report["type"] == "vc_report"
    data = report["data"]
    assert data["extraction"]["path-to-revenue"].endswith("We charge $300 a month.")
    assert "Offline summary" in data["diagnosis"]
    assert posted == []


def test_kb_search_endpoint_returns_structured_hits(client):
    body = client.post("/kb/search", json={"query": "first customers", "top_k": 2}).json()
    assert body["embedder_id"] == "stub/kb/-/0/p0"
    assert body["results"][1]["url"] == "https://sequoiacap.com/article/stripe"


def test_foreign_origins_are_rejected(client):
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("ws://127.0.0.1/ws/chat?mode=mentor", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_json()
    assert client.get("/memories", headers={"origin": "https://evil.example"}).status_code == 403
    assert client.get("/memories", headers={"origin": "http://127.0.0.1:3000"}).status_code == 200
    with client.websocket_connect("ws://127.0.0.1/ws/chat?mode=mentor", headers={"origin": "http://127.0.0.1:3000"}) as ws:
        assert ws.receive_json()["type"] == "agent_message"


def test_quoted_knowledge_base_text_is_plain():
    from scripted_llm import _plain

    assert _plain("**Go** to [the hosts](https://example.com) in `person`.") == "Go to the hosts in person."
    assert _plain("It grew.\n#### Airbnb Trends: #Ransackgate\n**Brian Chesky:** Trust is hard.") == "It grew.\n\nBrian Chesky: Trust is hard."


def test_foreign_host_header_is_refused(client):
    assert client.post("/kb/search", json={"query": "first customers"}, headers={"host": "attacker.example"}).status_code == 400
