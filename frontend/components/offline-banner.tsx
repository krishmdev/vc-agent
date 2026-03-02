import { OFFLINE } from "@/lib/mode"

// Offline builds say plainly what is simulated, so a demo is never mistaken for live output.
export function OfflineBanner() {
  if (!OFFLINE) return null
  return (
    <div
      role="note"
      data-testid="offline-banner"
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-secondary/95 px-4 py-1.5 text-center text-[11px] text-secondary-foreground backdrop-blur"
    >
      Offline demo, no keys or network: research replays recorded Gemini runs, the mentor is a scripted text chat,
      the knowledge base uses a local MiniLM index, memory is local SQLite, and founder domain tags are recorded.
    </div>
  )
}
