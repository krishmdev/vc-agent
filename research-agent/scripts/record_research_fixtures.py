"""Record live deep-research runs for the offline FixtureResearchProvider.

Needs network and GEMINI_API_KEY. Each run costs real money (the Deep Research agent runs many
searches), so only run this when the fixtures need refreshing:

    cd research-agent && uv run python scripts/record_research_fixtures.py [--only SLUG] [--force]

The prompt is built exactly the way the app builds its first research turn for an idea with no
dashboard answers yet, and its sha256 is stored. The replay labels a run "exact" only when the
app's prompt hashes to the same value; the same idea with extra context is labelled as such, and
any other idea falls back to the nearest sample with a banner saying so.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google import genai  # noqa: E402

import settings  # noqa: E402
from prompts import (  # noqa: E402
    build_context,
    build_deep_research_prompt,
    prompt_sha256,
)
from research_providers import GeminiResearchProvider, progress_notes  # noqa: E402

# Same first message research-chat.tsx sends when the panel opens.
FIRST_MESSAGE = "Start research based on provided context."

SAMPLES = [
    {
        "slug": "vet-clinic-software",
        "idea": (
            "Practice-management software for independent veterinary clinics that automates "
            "appointment reminders, inventory reordering, and pet-insurance claims."
        ),
        "follow_up": "Who are the main incumbents, and how do independent clinics choose software today?",
    },
    {
        "slug": "hardware-design-reviews",
        "idea": (
            "A marketplace that matches retired hardware engineers with early-stage hardware "
            "startups for paid, hourly design reviews."
        ),
        "follow_up": "How would this marketplace get its first 100 retired engineers to sign up?",
    },
    {
        "slug": "roommate-bill-splitting",
        "idea": (
            "An app for college students that splits and tracks shared rent, grocery, and "
            "utility bills between roommates and settles up automatically each month."
        ),
        "follow_up": "How do Splitwise and Venmo already cover this, and where is the gap?",
    },
]

OUT_DIR = settings.HERE / "fixtures" / "research"


def dump(obj):
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json", exclude_none=True)
    return obj


async def record(sample: dict, client: genai.Client, provider: GeminiResearchProvider) -> dict:
    context = build_context(idea=sample["idea"])
    prompt = build_deep_research_prompt([], context, FIRST_MESSAGE)
    started = time.monotonic()
    recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    interaction = await client.aio.interactions.create(
        input=prompt,
        agent=settings.DEEP_RESEARCH_AGENT,
        background=True,
        agent_config={"type": "deep-research", "thinking_summaries": "auto"},
    )
    print(f"[{sample['slug']}] interaction {interaction.id}", flush=True)

    progress: list[dict] = []
    statuses: list[dict] = []
    seen = 0
    while True:
        interaction = await client.aio.interactions.get(interaction.id)
        t = round(time.monotonic() - started, 1)
        if not statuses or statuses[-1]["status"] != interaction.status:
            statuses.append({"t": t, "status": interaction.status})
        notes = progress_notes(interaction.steps)
        for note in notes[seen:]:
            progress.append({"t": t, "note": note[:400]})
        seen = len(notes)
        if interaction.status == "completed":
            break
        if interaction.status in {"failed", "cancelled", "incomplete", "budget_exceeded"}:
            raise RuntimeError(f"{sample['slug']}: {interaction.status} {interaction.errors}")
        await asyncio.sleep(10)

    duration = round(time.monotonic() - started, 1)
    report = interaction.output_text
    print(f"[{sample['slug']}] done in {duration}s, {len(report)} chars", flush=True)

    history = [
        {"role": "user", "content": FIRST_MESSAGE},
        {"role": "assistant", "content": report},
    ]
    answer = await provider.follow_up(history, sample["follow_up"], context)

    return {
        "schema": 1,
        "slug": sample["slug"],
        "idea": sample["idea"],
        "first_message": FIRST_MESSAGE,
        "context": context,
        "prompt_sha256": prompt_sha256(prompt),
        "agent": settings.DEEP_RESEARCH_AGENT,
        "interaction_id": interaction.id,
        "recorded_at": recorded_at,
        "duration_s": duration,
        "statuses": statuses,
        "progress": progress,
        "usage": dump(interaction.usage),
        "report": report,
        "follow_ups": [
            {
                "question": sample["follow_up"],
                "model": settings.CHAT_MODEL,
                "grounding": "google_search",
                "answer": answer,
            }
        ],
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", action="append", help="slug to record (repeatable)")
    parser.add_argument("--force", action="store_true", help="overwrite existing fixtures")
    args = parser.parse_args()

    if settings.OFFLINE or not os.environ.get("GEMINI_API_KEY"):
        print("Recording needs live mode and GEMINI_API_KEY.", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    samples = [s for s in SAMPLES if not args.only or s["slug"] in args.only]
    todo = [s for s in samples if args.force or not (OUT_DIR / f"{s['slug']}.json").exists()]
    if not todo:
        print("Nothing to record.")
        return 0

    api_key = os.environ["GEMINI_API_KEY"]
    client = genai.Client(api_key=api_key)
    provider = GeminiResearchProvider(api_key)

    async def run_one(sample: dict) -> None:
        data = await record(sample, client, provider)
        path = OUT_DIR / f"{sample['slug']}.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path.relative_to(settings.HERE)}", flush=True)

    results = await asyncio.gather(*(run_one(s) for s in todo), return_exceptions=True)
    failed = [r for r in results if isinstance(r, Exception)]
    for exc in failed:
        print(f"error: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
