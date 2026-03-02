import { expect, test } from "@playwright/test"

// Every backend process type answers from inside its own process. Under the sandbox all probes
// must fail; EXPECT_EGRESS=open is the companion check, run unsandboxed, proving the probe works.
const expectOpen = process.env.EXPECT_EGRESS === "open"
const PROBES = [
  { name: "Next.js server runtime", url: "http://127.0.0.1:3000/api/diag/egress" },
  { name: "research agent (FastAPI)", url: "http://127.0.0.1:8000/_diag/egress" },
  { name: "voice agent server (mentor transport)", url: "http://127.0.0.1:8001/_diag/egress" },
]

for (const probe of PROBES) {
  test(`egress from ${probe.name} is ${expectOpen ? "open (companion check)" : "blocked"}`, async ({ request }) => {
    const res = await request.get(probe.url, { timeout: 30_000 })
    expect(res.ok()).toBeTruthy()
    const body = await res.json()
    console.log(`${body.process} pid=${body.pid} blocked=${body.blocked}`, JSON.stringify(body.results))
    expect(body.results).toHaveLength(4)
    expect(body.blocked).toBe(!expectOpen)
    if (expectOpen) expect(body.results.every((r: { connected: boolean }) => r.connected)).toBe(true)
  })
}

test("offline providers are active and no keys are visible", async ({ request }) => {
  const research = await (await request.get("http://127.0.0.1:8000/_diag/providers")).json()
  expect(research).toMatchObject({
    mode: "offline",
    research: "fixture",
    guides: "extractive",
    classifier: "recorded+keyword",
    gemini_key_visible: false,
  })
  const agent = await (await request.get("http://127.0.0.1:8001/_diag/providers")).json()
  expect(agent).toMatchObject({ mode: "offline", text_llm: "ScriptedLLM", memory: "LocalMemoryStore" })
  expect(agent.embedder_id).toMatch(/^local-onnx\/all-MiniLM-L6-v2\//)
})
