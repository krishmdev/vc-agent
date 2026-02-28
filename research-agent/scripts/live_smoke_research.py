"""Live smoke: one deep-research run through the running research agent, plus /health latency.

Needs the research agent running in live mode on :8000 (and the KB server on :8001). Costs one
deep-research run (roughly $1). Writes JSON to stdout.

    uv run python scripts/live_smoke_research.py > ../docs/verification/live-research-DATE.json
"""

import json
import statistics
import time

import httpx

BASE = "http://127.0.0.1:8000"
IDEA = "A subscription service that refurbishes and leases used lab equipment to early-stage biotech startups."


def main() -> None:
    out = {}
    t0 = time.time()
    r = httpx.post(f"{BASE}/chat", json={"message": "Start research based on provided context.", "idea": IDEA}, timeout=30).json()
    out["chat_response_ms"] = round((time.time() - t0) * 1000, 1)
    task, latencies, statuses, notes = r["task_id"], [], [], 0
    while True:
        t = time.time()
        httpx.get(f"{BASE}/health", timeout=10)
        latencies.append((time.time() - t) * 1000)
        s = httpx.get(f"{BASE}/chat/status/{task}", timeout=10).json()
        if not statuses or statuses[-1] != s["status"]:
            statuses.append(s["status"])
        notes = max(notes, len(s["progress"]))
        if s["status"] in ("completed", "failed"):
            break
        time.sleep(5)
    content = s.get("content") or ""
    out.update(
        idea=IDEA,
        statuses=statuses,
        provider=s["provider"],
        elapsed_s=s["elapsed_s"],
        max_progress_notes_seen=notes,
        health_probes=len(latencies),
        health_ms_median=round(statistics.median(latencies), 1),
        health_ms_max=round(max(latencies), 1),
        report_chars=len(content),
        report_has_market_assessment="MARKET SPACE ASSESSMENT" in content.upper(),
        error=s.get("error"),
    )
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
