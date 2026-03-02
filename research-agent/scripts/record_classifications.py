"""Record Gemini domain classifications for the synthetic sample founders.

Offline mode replays these (RecordedDomainClassifier) when the classifier input matches exactly,
so the sample scorecards use the same tags live mode would. Needs network and GEMINI_API_KEY;
eight calls to sierra-demo's classifier model (paced for a 5/minute limit), a few cents at most.

    uv run python scripts/record_classifications.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scoring.classifier import GeminiDomainClassifier, company_input_text, founder_input_text, input_key, recording_header  # noqa: E402
from scoring.domain_fit import company_evidence_level  # noqa: E402
from scoring.seen_greatness import SeenGreatnessScorer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "scoring"
OUT = ROOT / "recordings" / "classifications.json"


async def classify_with_retry(classifier: GeminiDomainClassifier, kind: str, text: str) -> dict:
    """Retries rate limits (429) and overload (503); anything else raises, so a fallback is never
    recorded as Gemini's answer."""
    for attempt in range(6):
        await asyncio.sleep(15)  # a 5-requests-per-minute limit applies on some keys
        try:
            return await classifier.classify_text(kind, text)
        except Exception as exc:
            if not ("429" in str(exc) or "503" in str(exc)) or attempt == 5:
                raise
            print(f"{str(exc)[:3]}, waiting ({attempt + 1}/6)", file=sys.stderr)
            await asyncio.sleep(60)
    raise RuntimeError("unreachable")


async def main() -> int:
    key = os.environ.get("GEMINI_API_KEY")
    if not key or os.environ.get("VC_AGENT_MODE") == "offline":
        print("Recording needs live mode and GEMINI_API_KEY.", file=sys.stderr)
        return 2
    classifier = GeminiDomainClassifier(key)
    recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    recordings = {}
    for path in sorted((ROOT / "fixtures").glob("*.json")):
        fx = json.loads(path.read_text())
        company = fx["company"]
        inputs = [
            ("founder", founder_input_text(fx, SeenGreatnessScorer().matched_categories(fx), company["name"])),
            ("company", company_input_text(company, company_evidence_level(company))),
        ]
        for kind, text in inputs:
            tags = await classify_with_retry(classifier, kind, text)
            recordings[input_key(kind, text)] = {
                "fixture": fx["id"],
                "kind": kind,
                "model": tags.pop("model"),
                "recorded_at": recorded_at,
                "tags": {k: v for k, v in tags.items() if k != "source"},
            }
            print(f"{fx['id']:26} {kind:8} {tags['primary_domain']}/{tags['primary_subdomain']}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"schema": 1, "header": recording_header(classifier.model), "recordings": recordings}, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
