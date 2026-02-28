"""Live smoke: Mem0 cloud add / get_all / search through memory.make_memory_store().

Uses a throwaway user id and deletes it afterwards (Mem0 deletes asynchronously; re-run
get_all a few seconds later to confirm). Needs MEM0_API_KEY.

    uv run python scripts/mem0_smoke.py > ../docs/verification/mem0-DATE.json
"""

import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memory import make_memory_store  # noqa: E402


async def main() -> None:
    store = make_memory_store()
    uid = f"vc-agent-smoke-{int(time.time())}"
    out = {"backend": type(store).__name__, "user_id": uid}
    t = time.time()
    out["add"] = await store.add([{"role": "user", "content": "We plan to charge each veterinary clinic $300 a month for the software."}], user_id=uid)
    out["add_s"] = round(time.time() - t, 2)
    for _ in range(12):  # Mem0 extracts memories in the background
        found = await store.get_all(user_id=uid, filters={"user_id": uid})
        if found.get("results"):
            break
        await asyncio.sleep(5)
    out["get_all_memories"] = [m.get("memory") for m in found.get("results", [])]
    s = await store.search("pricing", user_id=uid, filters={"user_id": uid})
    out["search_pricing"] = [m.get("memory") for m in s.get("results", [])][:3]
    await store.delete_all(user_id=uid)
    out["cleaned_up"] = True
    print(json.dumps(out, indent=2, default=str))


asyncio.run(main())
