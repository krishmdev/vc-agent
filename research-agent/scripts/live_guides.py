"""Live smoke: KB-grounded resource guides from the running research agent (live mode).

Prints one JSON line per question: the writer, which [n] citations the guide used, and the
retrieved sources. A few cents of gemini-2.5-flash.

    uv run python scripts/live_guides.py > ../docs/verification/live-guides-DATE.jsonl
"""

import json
import re

import httpx

QUESTIONS = ["How do I find my first customers?", "How should I think about pricing an early product?"]

for q in QUESTIONS:
    d = httpx.post("http://127.0.0.1:8000/generate_resource_article", json={"question": q, "module": "customer"}, timeout=120).json()
    print(json.dumps({
        "question": q,
        "writer": d.get("writer"),
        "cites_used": sorted(set(re.findall(r"\[(\d)\]", d.get("content", "")))),
        "citations": [c["source"] for c in d.get("citations", [])],
        "error": d.get("detail"),
    }))
