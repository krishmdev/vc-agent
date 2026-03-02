import os from "node:os"
import path from "node:path"
import { defineConfig, devices } from "@playwright/test"

// Offline e2e: all three services run in offline mode on localhost. Run the whole thing inside a
// network sandbox (`offline-run make e2e-offline` on macOS, a `--network none` container in CI);
// the egress spec fails if any backend process can reach the internet.
const root = path.resolve(__dirname, "..")
const memoryDb = path.join(os.tmpdir(), `vc-agent-e2e-${Date.now()}.sqlite3`)
const noKeys = {
  OPENAI_API_KEY: "",
  GEMINI_API_KEY: "",
  GOOGLE_API_KEY: "",
  MEM0_API_KEY: "",
  LIVEKIT_API_KEY: "",
  LIVEKIT_API_SECRET: "",
}
const offline = { ...noKeys, VC_AGENT_MODE: "offline", VC_AGENT_DIAGNOSTICS: "1", HF_HUB_OFFLINE: "1" }
// The research agent's port can move if 8000 is taken (E2E_RESEARCH_PORT); Next reaches it
// through RESEARCH_SERVICE_URL at runtime. The agent server stays on 8001 because the browser's
// WebSocket URL is baked into the offline build.
const researchPort = process.env.E2E_RESEARCH_PORT ?? "8000"
export const RESEARCH_URL = `http://127.0.0.1:${researchPort}`

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } } }],
  webServer: [
    {
      command: ".venv/bin/python -m uvicorn server:app --host 127.0.0.1 --port 8001",
      cwd: path.join(root, "livekit-voice-agent"),
      url: "http://127.0.0.1:8001/health",
      env: { ...offline, VC_AGENT_MEMORY_DB: memoryDb, FRONTEND_URL: "http://127.0.0.1:3000" },
      timeout: 120_000,
      stdout: "pipe",
    },
    {
      command: `.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port ${researchPort}`,
      cwd: path.join(root, "research-agent"),
      url: `${RESEARCH_URL}/health`,
      env: { ...offline, RESEARCH_FIXTURE_REPLAY_SECONDS: process.env.RESEARCH_FIXTURE_REPLAY_SECONDS ?? "6" },
      timeout: 60_000,
      stdout: "pipe",
    },
    {
      command: "npx next start -H 127.0.0.1 -p 3000",
      cwd: __dirname,
      url: "http://127.0.0.1:3000",
      env: {
        ...noKeys,
        NEXT_DIST_DIR: ".next-offline",
        NEXT_PUBLIC_VC_AGENT_MODE: "offline",
        VC_AGENT_DIAGNOSTICS: "1",
        NEXT_TELEMETRY_DISABLED: "1",
        RESEARCH_SERVICE_URL: RESEARCH_URL,
      },
      timeout: 60_000,
      stdout: "pipe",
    },
  ],
})
