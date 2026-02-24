"""Live-mode providers against fake async clients (no network, no keys)."""

from types import SimpleNamespace as NS

from guides import GeminiGuideWriter, citations_for, sources_block
from kb_client import Passage
from research_providers import GeminiResearchProvider, progress_notes


class FakeInteractions:
    def __init__(self):
        self.polls = 0

    async def create(self, **kwargs):
        assert kwargs["background"] is True
        assert kwargs["agent_config"] == {"type": "deep-research", "thinking_summaries": "auto"}
        return NS(id="int-1")

    async def get(self, interaction_id):
        self.polls += 1
        steps = [NS(type="thought", summary=[NS(text="Mapping the landscape")])]
        if self.polls >= 2:
            steps.append(NS(type="google_search_call", arguments=NS(queries=["vet software market size"])))
        if self.polls < 3:
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
