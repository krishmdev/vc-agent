"""Live-mode providers against fake async clients (no network, no keys)."""

from types import SimpleNamespace as NS

from guides import GeminiGuideWriter, citations_for, sources_block
from kb_client import Passage
from research_providers import GeminiResearchProvider, progress_notes


class FakeInteractions:
    def __init__(self, finish_after=3):
        self.polls = 0
        self.finish_after = finish_after
        self.cancelled = []

    async def cancel(self, interaction_id):
        self.cancelled.append(interaction_id)
        return NS(status="cancelled")

    async def create(self, **kwargs):
        assert kwargs["background"] is True
        assert kwargs["agent_config"] == {"type": "deep-research", "thinking_summaries": "auto"}
        return NS(id="int-1")

    async def get(self, interaction_id):
        self.polls += 1
        steps = [NS(type="thought", summary=[NS(text="Mapping the landscape")])]
        if self.polls >= 2:
            steps.append(NS(type="google_search_call", arguments=NS(queries=["vet software market size"])))
        if self.polls < self.finish_after:
            return NS(status="in_progress", steps=steps, output_text="", errors=None)
        return NS(status="completed", steps=steps, output_text="# MARKET SPACE ASSESSMENT", errors=None)


async def test_deep_research_polls_asynchronously_and_reports_progress():
    provider = GeminiResearchProvider("test-key", poll_interval=0)
    fake = FakeInteractions()
    provider._client = NS(aio=NS(interactions=fake))
    events = []
    report = await provider.deep_research("prompt", context="Idea: x", on_progress=lambda s, n: events.append((s, n)))
    assert report == "# MARKET SPACE ASSESSMENT"
    notes = [n for _, n in events]
    assert "Mapping the landscape" in notes
    assert "Searching: vet software market size" in notes
    assert notes.count("Mapping the landscape") == 1  # each note reported once across polls


async def test_timed_out_deep_research_is_cancelled_remotely():
    import pytest

    from research_providers import ResearchError

    provider = GeminiResearchProvider("test-key", poll_interval=0, timeout_s=0)
    fake = FakeInteractions(finish_after=99)
    provider._client = NS(aio=NS(interactions=fake))
    with pytest.raises(ResearchError, match="timed out"):
        await provider.deep_research("prompt", context="Idea: x", on_progress=lambda s, n: None)
    assert fake.cancelled == ["int-1"]


async def test_cancelled_job_cancels_the_remote_run():
    import asyncio

    provider = GeminiResearchProvider("test-key", poll_interval=0.01)
    fake = FakeInteractions(finish_after=10**9)
    provider._client = NS(aio=NS(interactions=fake))
    job = asyncio.create_task(provider.deep_research("prompt", context="Idea: x", on_progress=lambda s, n: None))
    await asyncio.sleep(0.05)
    job.cancel()
    try:
        await job
    except asyncio.CancelledError:
        pass
    assert fake.cancelled == ["int-1"]


def test_progress_notes_ignore_unknown_steps():
    assert progress_notes([NS(type="model_output"), NS(type="thought", summary=[])]) == []


async def test_gemini_guide_prompt_includes_numbered_passages():
    seen = {}

    async def generate_content(**kwargs):
        seen.update(kwargs)
        return NS(text="**Core Principle**\n\nMeet users in person [1].")

    writer = GeminiGuideWriter("test-key")
    writer._client = NS(aio=NS(models=NS(generate_content=generate_content)))
    passages = [Passage("[From: Airbnb]\nThey met hosts in person.", "Airbnb", "transcript", None, 0.7)]
    out = await writer.write_guide("How do I find early users?", passages)
    assert out.endswith("[1].")
    assert "[1] Airbnb (transcript)\nThey met hosts in person." in seen["contents"]
    assert seen["config"].tools is None  # Search would drop the [n] citations
    assert citations_for(passages)[0]["snippet"] == "They met hosts in person."
    assert sources_block([]) == ""
