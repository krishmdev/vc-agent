import { OFFLINE } from "@/lib/mode"

// Shown in each full-height panel header in offline builds.
export function OfflineChip() {
  if (!OFFLINE) return null
  return (
    <span data-testid="offline-chip" className="rounded-full border border-border bg-secondary px-2 py-0.5 text-[10px] font-medium text-secondary-foreground">
      Offline demo
    </span>
  )
}
