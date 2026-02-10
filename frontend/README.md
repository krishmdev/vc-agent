# Launchpad — Frontend

The web app for **Launchpad**, an AI‑guided startup‑validation studio. This is the
user‑facing surface of a three‑service system; see the [root README](../README.md)
for the full picture and the [research agent](../research-agent) and
[voice agent](../livekit-voice-agent) for the backends.

Built with **Next.js 16** (App Router), **React 19**, **TypeScript**,
**Tailwind CSS v4**, and **shadcn/ui**.

## Pages

| Route | Purpose |
|-------|---------|
| `/` | Landing + startup‑idea input |
| `/mentorship` | AI mentor voice call (LiveKit, `mode=mentor`) |
| `/dashboard` | Main 5‑tier validation hub + feature launchers |
| `/vc-call` | VC pitch voice call (LiveKit, `mode=vc`) → generates a report |
| `/investor-memo` | Printable, compiled investment memo |

## API routes

All secrets stay server‑side in these route handlers under `app/api/`:

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/api/token` | Mints a LiveKit JWT with persona metadata (`room`, `mode`, `idea`) via `livekit-server-sdk`. |
| `POST` / `GET` | `/api/research` | Proxies to the research agent's `/chat` + `/chat/status/{id}`. |
| `POST` / `GET` | `/api/customer-reachout` | Proxies to the research agent's `/customer-reachout` + status. |
| `POST` / `GET` | `/api/vc-report` | Stores the VC report (posted by the voice agent) / long‑polls for it. |
| `GET` | `/api/memories` | Fetches the founder's memories from Mem0. |
| `POST` | `/api/extract-fields` | Maps memory text onto the 20 dashboard fields (Jaccard similarity + Gemini `gemini-2.5-flash` fallback). |

## Architecture notes

- **State** lives in a persisted **Zustand** store (`launchpad-storage-v2` in
  `localStorage`). The dashboard schema (5 tiers × 4 questions) is defined in
  `lib/dashboard-data.ts`; VC state is intentionally excluded from persistence so
  it resets each session.
- **Voice UI** uses `@livekit/components-react` (`LiveKitRoom`,
  `useVoiceAssistant`, `BarVisualizer`) in audio‑only mode. The agent persona
  (`mentor` / `vc`) is chosen by embedding `{ startupIdea, agentMode }` into the
  LiveKit token metadata (see `/api/token`).
- **VC report flow:** `/vc-call` publishes a LiveKit data message
  `{ type: "generate_report" }` to the agent on "End Pitch"; the agent POSTs the
  finished report to `/api/vc-report`, which `/dashboard` long‑polls to display and
  auto‑fill fields.
- **Styling:** Tailwind CSS v4 (CSS‑based config in `app/globals.css`, no
  `tailwind.config.js`) + shadcn/ui ("new‑york" style) with a Sequoia‑inspired
  earthy‑green oklch palette. Icons from `lucide-react`.

## Environment variables

Create `frontend/.env.local` (or use the shared `.env.local` at the repo root):

```env
# LiveKit (token minting)
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-api-key
LIVEKIT_API_SECRET=your-api-secret

# Mem0 (voice-chat memory sync)
MEM0_API_KEY=your-mem0-key
MEM0_USER_ID=sequoia-mentor-agent   # optional; this is the default

# Gemini (field-extraction fallback)
GEMINI_API_KEY=your-gemini-key

# Research backend base URL (optional; defaults to http://127.0.0.1:8000)
RESEARCH_SERVICE_URL=http://127.0.0.1:8000
```

> **Note:** the research backend URL is hard‑coded to `http://127.0.0.1:8000` in
> the proxy routes and to `http://localhost:8000` in
> `components/resource-drawer.tsx` (which calls the backend directly). Set
> `RESEARCH_SERVICE_URL` and parameterize the resource drawer before deploying.

## Development

```bash
npm install
npm run dev        # http://localhost:3000  (Turbopack disabled: TURBOPACK=0)
npm run build      # production build
npm run start      # serve the production build
npm run lint       # eslint
```

The research agent (`:8000`) and the LiveKit voice agent must be running for the
research, customer‑reachout, resource, and voice features to work. The easiest way
to boot everything together is `zsh start.sh` from the repo root.
