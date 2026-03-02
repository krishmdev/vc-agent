"""The offline composition through the real HTTP routes and task/status polling flow."""

import asyncio
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

import main
import settings
from fixture_research import load_fixtures
from kb_client import KnowledgeBaseClient
from prompts import build_context, build_deep_research_prompt, prompt_sha256

FIXTURES = load_fixtures(settings.FIXTURE_DIR)
FIRST_MESSAGE = "Start research based on provided context."

KB_RESULTS = [
    {"text": "[From: Airbnb ft Brian Chesky]\nThe founders flew to New York and met every host in person. They took the listing photos themselves because the old ones looked terrible.",
     "source": "Airbnb ft Brian Chesky", "type": "transcript", "url": None, "score": 0.71},
    {"text": "[From: The Arc PMF Framework]\nFounders should find the customers whose hair is on fire and serve them before anyone else.",
     "source": "The Arc PMF Framework", "type": "website", "url": "https://sequoiacap.com/article/pmf-framework", "score": 0.52},
]


def kb_transport(status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/kb/search"
        if status != 200:
            return httpx.Response(status, json={"detail": "index not built"})
        body = json.loads(request.content)
        return httpx.Response(200, json={"embedder_id": "local-onnx/test/-/384/p0", "results": KB_RESULTS[: body["top_k"]]})
    return httpx.MockTransport(handler)


@pytest.fixture
def client():
    with TestClient(main.app, base_url="http://127.0.0.1") as c:
        main.app.state.kb = KnowledgeBaseClient("http://kb.test", transport=kb_transport())
        yield c


def poll(client, task_id, timeout=10):
    seen = []
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/chat/status/{task_id}").json()
        seen.append(body["status"])
        if body["status"] in main.TERMINAL:
            return body, seen
        time.sleep(0.05)
    raise AssertionError(f"task did not finish: {seen[-5:]}")


def test_three_fixtures_record_model_date_and_the_apps_exact_prompt():
    assert len(FIXTURES) == 3
    for fx in FIXTURES:
        d = fx.data
        assert d["agent"].startswith("deep-research") and d["recorded_at"][:4] == "2026"
        assert len(d["report"]) > 5000 and d["follow_ups"][0]["answer"]
        prompt = build_deep_research_prompt([], build_context(idea=d["idea"]), FIRST_MESSAGE)
        assert prompt_sha256(prompt) == d["prompt_sha256"]


def test_research_replays_through_queued_running_completed(client):
    fx = FIXTURES[0]
    start = client.post("/chat", json={"message": FIRST_MESSAGE, "idea": fx.idea}).json()
    assert start["status"] == "queued"
    final, seen = poll(client, start["task_id"])
    assert final["status"] == "completed" and final["provider"] == "fixture"
    assert "running" in seen
    assert final["progress"][-1] == fx.data["progress"][-1]["note"]  # recorded notes replayed in order
    assert final["content"].startswith("> Offline mode: replaying the exact deep-research recording for this prompt")
    assert fx.data["report"] in final["content"]

    follow = client.post(
        "/chat", json={"message": fx.data["follow_ups"][0]["question"], "session_id": start["session_id"], "idea": fx.idea}
    ).json()
    answer, _ = poll(client, follow["task_id"])
    assert answer["kind"] == "follow_up"
    assert answer["content"] == fx.data["follow_ups"][0]["answer"]


def test_same_idea_with_extra_context_is_not_labelled_exact(client):
    fx = FIXTURES[1]
    start = client.post("/chat", json={"message": FIRST_MESSAGE, "idea": fx.idea, "customer": "Hardware teams in Shenzhen"}).json()
    final, _ = poll(client, start["task_id"])
    assert final["content"].startswith("> Offline mode: same idea, different context.")


def test_unknown_idea_uses_the_closest_recording_and_says_so(client):
    start = client.post("/chat", json={"message": FIRST_MESSAGE, "idea": "Scheduling software for small veterinary practices"}).json()
    final, _ = poll(client, start["task_id"])
    assert "closest sample idea" in final["content"]
    assert "veterinary" in final["content"].split("\n")[0].lower()


def test_guide_is_grounded_in_kb_passages_with_citations(client):
    body = client.post("/generate_resource_article", json={"question": "How do founders find their first customers in person?", "module": "customer"}).json()
    assert body["writer"] == "extractive"
    assert body["embedder_id"] == "local-onnx/test/-/384/p0"
    assert [c["n"] for c in body["citations"]] == [1, 2]
    assert body["citations"][1]["url"] == "https://sequoiacap.com/article/pmf-framework"
    assert "[1]" in body["content"] and "Airbnb ft Brian Chesky" in body["content"]
    assert not body["citations"][0]["snippet"].startswith("[From:")

    chat = client.post("/resource_chat", json={"message": "What did Airbnb do with the photos?", "history": [], "resource_context": body["content"]}).json()
    assert "photos" in chat["message"] and "[1]" in chat["message"]


def test_offline_guide_fails_clearly_when_kb_is_down(client):
    main.app.state.kb = KnowledgeBaseClient("http://kb.test", transport=kb_transport(status=503))
    resp = client.post("/generate_resource_article", json={"question": "x", "module": "customer"})
    assert resp.status_code == 503


def test_reachout_and_slides_are_labelled_off_in_offline_mode(client):
    task = client.post("/customer-reachout", json={"icp_description": "vet clinics", "customer_type": "B2C"}).json()
    body, _ = poll(client, task["task_id"])
    assert "offline mode" in json.loads(body["content"])["forums"][0]["strategy"]

    task = client.post("/generate-slides", json={"modules": {}, "idea": "x"}).json()
    body, _ = poll(client, task["task_id"])
    assert body["status"] == "failed" and "offline mode" in body["error"]


async def test_event_loop_stays_free_while_research_runs():
    """A slow research turn must not block other requests (handlers are async all the way)."""
    from fixture_research import FixtureResearchProvider

    provider = FixtureResearchProvider(settings.FIXTURE_DIR, replay_seconds=1.5)
    task = asyncio.create_task(
        provider.deep_research("p", context=f"Idea: {FIXTURES[0].idea}", on_progress=lambda *_: None)
    )
    ticks = 0
    started = time.monotonic()
    while not task.done():
        await asyncio.sleep(0.05)
        ticks += 1
    assert time.monotonic() - started >= 1.4
    assert ticks >= 20


def test_follow_up_during_first_turn_is_rejected(client):
    fx = FIXTURES[0]
    start = client.post("/chat", json={"message": FIRST_MESSAGE, "idea": fx.idea}).json()
    again = client.post("/chat", json={"message": "and competitors?", "session_id": start["session_id"], "idea": fx.idea})
    assert again.status_code == 409
    poll(client, start["task_id"])
    assert client.post("/chat", json={"message": "and competitors?", "session_id": start["session_id"], "idea": fx.idea}).status_code == 200


def test_finished_tasks_are_evicted_after_the_ttl():
    main.active_tasks.clear()
    main.active_tasks["old"] = {"status": "completed", "started": 0.0, "finished": 0.0}
    main.active_tasks["running"] = {"status": "running", "started": 0.0}
    main.evict_tasks(now=main.TASK_TTL_S + 1)
    assert list(main.active_tasks) == ["running"]


def test_running_jobs_are_cancelled_at_shutdown():
    fx = FIXTURES[0]
    with TestClient(main.app, base_url="http://127.0.0.1") as c:
        start = c.post("/chat", json={"message": FIRST_MESSAGE, "idea": fx.idea}).json()
        assert main.active_tasks[start["task_id"]]["status"] not in main.TERMINAL
    task = main.active_tasks[start["task_id"]]
    assert task["status"] == "cancelled" and "Cancelled" in task["error"]
    assert not main.running_jobs and start["session_id"] not in main.sessions_in_flight


def test_new_work_is_refused_past_the_running_cap(client, monkeypatch):
    monkeypatch.setattr(main, "MAX_RUNNING_JOBS", 0)
    r = client.post("/chat", json={"message": FIRST_MESSAGE, "idea": FIXTURES[0].idea})
    assert r.status_code == 503


def test_jobs_running_past_the_backstop_are_cancelled(client):
    start = client.post("/chat", json={"message": FIRST_MESSAGE, "idea": FIXTURES[0].idea}).json()
    # On the server's loop, where the job runs; Task.cancel isn't thread-safe.
    client.portal.call(lambda: main.evict_tasks(now=time.monotonic() + main.RUNNING_TTL_S + 1))
    body, _ = poll(client, start["task_id"])
    assert body["status"] == "cancelled"


def test_idle_chat_sessions_are_evicted():
    main.chat_sessions.clear()
    main.session_touched.clear()
    main.chat_sessions.update({"idle": [], "fresh": [], "busy": []})
    main.session_touched.update({"idle": 0.0, "fresh": main.SESSION_TTL_S, "busy": 0.0})
    main.sessions_in_flight.add("busy")
    try:
        main.evict_sessions(now=main.SESSION_TTL_S + 1)
    finally:
        main.sessions_in_flight.discard("busy")
    assert sorted(main.chat_sessions) == ["busy", "fresh"]


def test_guide_snippets_are_plain_text_and_headings_need_bullets():
    import asyncio

    from guides import ExtractiveGuideWriter, _snippet
    from kb_client import Passage

    assert _snippet("[From: X]\n**Bold** words with a [link](https://example.com) and `code`.") == "Bold words with a link and code."
    one = [Passage("[From: A]\nFounders should meet their first customers in person.", "A", "website", None, 0.5)]
    guide = asyncio.run(ExtractiveGuideWriter().write_guide("How do founders meet customers?", one))
    assert "What founders in the knowledge base said" not in guide


def test_foreign_host_header_is_refused(client):
    assert client.get("/founder/samples").status_code == 200
    assert client.get("/founder/samples", headers={"host": "attacker.example"}).status_code == 400
