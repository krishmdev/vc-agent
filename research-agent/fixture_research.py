"""Offline research provider: replays deep-research runs recorded from the live Gemini agent.

Recordings live in fixtures/research/*.json and are produced by
scripts/record_research_fixtures.py (a separate, network-allowed step). Each file stores the
idea, the exact prompt hash, the agent id, the recording date, the progress notes with their
timestamps, the final report, and one recorded follow-up answer.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from pathlib import Path

import settings
from research_providers import ProgressFn, ResearchError
from textutil import best_sentences, jaccard

FOLLOW_UP_MATCH = 0.5


@dataclass
class Fixture:
    path: Path
    data: dict

    @property
    def idea(self) -> str:
        return self.data["idea"]


def load_fixtures(directory: Path) -> list[Fixture]:
    fixtures = []
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or not data.get("report"):
            raise ValueError(f"{path.name} is not a research fixture")
        fixtures.append(Fixture(path, data))
    return fixtures


def idea_from_context(context: str) -> str:
    match = re.search(r"^Idea:\s*(.+)$", context, re.MULTILINE)
    return match.group(1).strip() if match else context.strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


class FixtureResearchProvider:
    name = "fixture"

    def __init__(self, directory: Path, replay_seconds: float | None = None) -> None:
        self.fixtures = load_fixtures(directory)
        if not self.fixtures:
            raise ResearchError(f"No research fixtures in {directory}")
        self.replay_seconds = (
            settings.FIXTURE_REPLAY_SECONDS if replay_seconds is None else replay_seconds
        )

    def select(self, context: str) -> tuple[Fixture, bool]:
        idea = idea_from_context(context)
        for fx in self.fixtures:
            if _normalize(fx.idea) == _normalize(idea):
                return fx, True
        best = max(self.fixtures, key=lambda fx: jaccard(fx.idea, idea))
        return best, False

    async def deep_research(self, prompt: str, *, context: str, on_progress: ProgressFn) -> str:
        fx, exact = self.select(context)
        data = fx.data
        window = max(self.replay_seconds, 0.0)

        on_progress("queued", "Waiting for a research slot")
        await asyncio.sleep(window * 0.1)
        on_progress("running", f"Deep research started ({data['agent']}, recorded {data['recorded_at'][:10]})")

        duration = max(float(data.get("duration_s") or 1.0), 1.0)
        elapsed = window * 0.1
        for entry in data.get("progress", []):
            target = window * 0.1 + window * 0.85 * min(float(entry["t"]) / duration, 1.0)
            if target > elapsed:
                await asyncio.sleep(target - elapsed)
                elapsed = target
            on_progress("running", entry["note"])
        await asyncio.sleep(max(window - elapsed, 0.0))

        if exact:
            banner = (
                f"> Offline mode: replaying a deep-research report recorded on "
                f"{data['recorded_at'][:10]} with `{data['agent']}`."
            )
        else:
            banner = (
                "> Offline mode: there is no recording for this exact idea, so this is the recorded "
                f"report for the closest sample idea: \"{fx.idea}\"."
            )
        return f"{banner}\n\n{data['report']}"

    async def follow_up(self, history: list[dict[str, str]], user_message: str, context: str) -> str:
        fx, _ = self.select(context)
        for recorded in fx.data.get("follow_ups", []):
            if jaccard(recorded["question"], user_message) >= FOLLOW_UP_MATCH:
                return recorded["answer"]

        picks = best_sentences(user_message, fx.data["report"], k=3, min_len=40, max_len=400)
        if not picks:
            return (
                "Offline mode only has the recorded report for this idea, and nothing in it "
                "matches that question. Live mode answers follow-ups with Gemini and Google Search."
            )
        body = " ".join(picks)
        return (
            f"{body}\n\n_Offline mode: these sentences come from the recorded report. Live mode "
            "answers follow-ups with Gemini and Google Search._"
        )
