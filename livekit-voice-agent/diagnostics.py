"""Egress canary: tries to open TCP connections to a few external hosts from inside this process.

Served at /_diag/egress when VC_AGENT_DIAGNOSTICS=1. The offline e2e asserts every probe fails;
the unsandboxed companion check asserts they succeed, so the test can't pass vacuously.
"""

import asyncio
import os

TARGETS = [
    ("1.1.1.1", 443),
    ("api.openai.com", 443),
    ("generativelanguage.googleapis.com", 443),
    ("huggingface.co", 443),
]


async def probe_egress(process: str, timeout: float = 3.0) -> dict:
    results = []
    for host, port in TARGETS:
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
            writer.close()
            results.append({"target": f"{host}:{port}", "connected": True})
        except (OSError, asyncio.TimeoutError) as exc:
            results.append(
                {
                    "target": f"{host}:{port}",
                    "connected": False,
                    "error": f"{type(exc).__name__}: {exc}"[:160],
                }
            )
    return {
        "process": process,
        "pid": os.getpid(),
        "blocked": not any(r["connected"] for r in results),
        "results": results,
    }
