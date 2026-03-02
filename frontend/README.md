# Launchpad frontend

Next.js 16 (App Router, React 19, TypeScript, Tailwind CSS 4, shadcn/ui). Part of
[Launchpad](../README.md).

| Route | Purpose |
|-------|---------|
| `/` | Landing and idea input |
| `/mentorship` | Mentor call (LiveKit voice, or the text chat panel in offline builds) |
| `/dashboard` | 5-tier validation hub, research panel, resource drawer, floating mentor |
| `/vc-call` | VC pitch, then the post-call report |
| `/investor-memo` | Printable memo |

API routes under `app/api/` keep secrets on the server. `token` mints LiveKit JWTs with
`{startupIdea, agentMode}` metadata. `research`, `customer-reachout`, `resource-article` and
`resource-chat` proxy the research agent. `vc-report` holds the latest report for long polling.
`memories` reads Mem0 (or the local store through the voice-agent server when offline).
`extract-fields` maps memories onto dashboard questions. `diag/egress` is the network canary,
served only when `VC_AGENT_DIAGNOSTICS=1`.

The persisted Zustand store holds app state (`lib/store.ts`); the dashboard schema is in
`lib/dashboard-data.ts`.

## Modes

`NEXT_PUBLIC_VC_AGENT_MODE=offline` is inlined at build time and swaps every LiveKit widget for
`components/text-agent-chat.tsx`, which talks to `ws://127.0.0.1:8001/ws/chat`. Offline builds
go to `.next-offline` so they don't overwrite a live build. Route handlers also check
`VC_AGENT_MODE` at runtime (`lib/services.ts`), and `/api/token` returns 409 offline.

```bash
npm ci
npm run dev                                                          # live, :3000
NEXT_PUBLIC_VC_AGENT_MODE=offline NEXT_DIST_DIR=.next-offline npx next build
npx playwright test                                                  # offline e2e (starts all three services)
```

`e2e/journey.spec.ts` walks the offline product end to end, and `e2e/egress.spec.ts` checks that
no backend process can reach the internet. Run them inside a network sandbox; see the root
README.
