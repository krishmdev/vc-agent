import { OFFLINE } from "@/lib/mode"

// Offline builds say plainly what is simulated, so a demo is never mistaken for live output.
// One line at every width (its height is reserved as --banner-h in the root layout); the full
// list opens from "Details".
export function OfflineBanner() {
  if (!OFFLINE) return null
  return (
    <div
      role="note"
      data-testid="offline-banner"
      className="fixed inset-x-0 bottom-0 z-40 flex h-[var(--banner-h)] items-center justify-center gap-2 border-t border-border bg-secondary px-3 text-[11px] text-secondary-foreground"
    >
      <span className="truncate">Offline demo: no keys or network, providers simulated.</span>
      <details className="group relative shrink-0">
        <summary className="cursor-pointer select-none rounded px-1 font-medium underline decoration-dotted underline-offset-2 focus-visible:outline-2 focus-visible:outline-ring">
          Details
        </summary>
        <p className="absolute bottom-7 right-0 w-[min(22rem,calc(100vw-1.5rem))] rounded-lg border border-border bg-card p-3 text-left text-xs leading-relaxed text-foreground shadow-lg">
          Research replays recorded Gemini runs, the mentor is a scripted text chat, the knowledge base uses a local MiniLM
          index, memory is local SQLite, and founder domain tags are recorded.
        </p>
      </details>
    </div>
  )
}
