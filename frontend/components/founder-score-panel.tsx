"use client"

import { useEffect, useState } from "react"
import { AlertCircle, ArrowLeft, Loader2, Plus, Trash2, UserRound, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { FounderScorecardView } from "@/components/founder-scorecard"
import {
  fetchSampleScore,
  fetchSamples,
  scoreProfile,
  useFounderScore,
  type ExperienceInput,
  type SampleFounder,
} from "@/lib/founder-score"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { OfflineChip } from "@/components/offline-chip"

// Server and network errors in words a founder can act on.
function friendly(e: unknown): string {
  const msg = e instanceof Error ? e.message : String(e)
  if (/reachable|fetch|network/i.test(msg)) return "The scoring service isn't reachable. Check that the research agent is running, then try again."
  if (/422|invalid|date|pattern/i.test(msg)) return "Something in the form doesn't parse. Dates are YYYY or YYYY-MM, and a role can't end before it starts."
  return "Scoring didn't finish. Try again."
}

const inputCls =
  "w-full rounded-md border border-border bg-background px-2.5 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"

function ProfileForm({ onScored }: { onScored: () => void }) {
  const { idea, founder } = useAppStore()
  const setScorecard = useFounderScore((s) => s.setScorecard)
  const [name, setName] = useState(founder.name || "")
  const [roles, setRoles] = useState<ExperienceInput[]>([{ title: "", company: "", start_date: "", end_date: "" }])
  const [school, setSchool] = useState("")
  const [degree, setDegree] = useState("")
  const [major, setMajor] = useState("")
  const [companyName, setCompanyName] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const update = (i: number, patch: Partial<ExperienceInput>) => setRoles((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)))
  const hasRole = roles.some((r) => r.title.trim() && r.company.trim())

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      const experience = roles
        .filter((r) => r.title.trim() && r.company.trim())
        .map((r) => ({ ...r, start_date: r.start_date || undefined, end_date: r.end_date || undefined }))
      const card = await scoreProfile(
        {
          name: name.trim() || "You",
          current_title: companyName.trim() ? "Founder" : undefined,
          experience: companyName.trim() ? [{ title: "Founder", company: companyName.trim() }, ...experience] : experience,
          education: school.trim() ? [{ school: school.trim(), degree: degree.trim(), major: major.trim() }] : [],
        },
        companyName.trim() ? { name: companyName.trim(), description: idea || "" } : null
      )
      setScorecard(card, { kind: "profile" })
      onScored()
    } catch (e) {
      setError(friendly(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={(e) => { e.preventDefault(); submit() }} className="space-y-4" data-testid="founder-profile-form">
      <p className="text-sm text-muted-foreground">
        Roles most recent first. Dates as YYYY or YYYY-MM; leave the end blank for a current role. Your idea from the home page is used as
        the company description.
      </p>
      <label className="block text-xs font-medium text-foreground">
        Name
        <input className={cn(inputCls, "mt-1")} value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="block text-xs font-medium text-foreground">
        Your company&apos;s name
        <input className={cn(inputCls, "mt-1")} value={companyName} onChange={(e) => setCompanyName(e.target.value)} placeholder="Leave blank to skip domain fit" />
      </label>
      <fieldset className="space-y-2">
        <legend className="text-xs font-medium text-foreground">Prior roles</legend>
        {roles.map((r, i) => (
          <div key={i} className="grid grid-cols-2 gap-2 rounded-lg border border-border p-2 sm:grid-cols-[1.3fr_1.2fr_0.7fr_0.7fr_auto] sm:items-end">
            <label className="col-span-2 text-[11px] font-medium text-muted-foreground sm:col-span-1">
              Title
              <input aria-label={`Role ${i + 1} title`} className={cn(inputCls, "mt-0.5")} placeholder="Senior Engineer" value={r.title} onChange={(e) => update(i, { title: e.target.value })} />
            </label>
            <label className="col-span-2 text-[11px] font-medium text-muted-foreground sm:col-span-1">
              Company
              <input aria-label={`Role ${i + 1} company`} className={cn(inputCls, "mt-0.5")} placeholder="Company" value={r.company} onChange={(e) => update(i, { company: e.target.value })} />
            </label>
            <label className="text-[11px] font-medium text-muted-foreground">
              Start
              <input aria-label={`Role ${i + 1} start`} className={cn(inputCls, "mt-0.5")} placeholder="2019" inputMode="numeric" value={r.start_date} onChange={(e) => update(i, { start_date: e.target.value })} />
            </label>
            <label className="text-[11px] font-medium text-muted-foreground">
              End
              <input aria-label={`Role ${i + 1} end`} className={cn(inputCls, "mt-0.5")} placeholder="blank if current" inputMode="numeric" value={r.end_date} onChange={(e) => update(i, { end_date: e.target.value })} />
            </label>
            <Button type="button" variant="ghost" size="icon" className="col-span-2 justify-self-end sm:col-span-1" aria-label={`Remove role ${i + 1}`} disabled={roles.length === 1} onClick={() => setRoles((rs) => rs.filter((_, j) => j !== i))}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
        <Button type="button" variant="outline" size="sm" className="gap-1.5" onClick={() => setRoles((rs) => [...rs, { title: "", company: "", start_date: "", end_date: "" }])}>
          <Plus className="h-3.5 w-3.5" /> Add role
        </Button>
      </fieldset>
      <fieldset className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <legend className="mb-1 text-xs font-medium text-foreground">Highest degree</legend>
        <input aria-label="School" className={inputCls} placeholder="School" value={school} onChange={(e) => setSchool(e.target.value)} />
        <input aria-label="Degree" className={inputCls} placeholder="Degree (BS, MS, PhD)" value={degree} onChange={(e) => setDegree(e.target.value)} />
        <input aria-label="Major" className={inputCls} placeholder="Major" value={major} onChange={(e) => setMajor(e.target.value)} />
      </fieldset>
      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <span className="flex-1 text-foreground/85">{error}</span>
          <Button type="submit" variant="outline" size="sm" className="h-7">Retry</Button>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" disabled={busy || !hasRole} aria-describedby="founder-form-hint" className="gap-2">
          {busy && <Loader2 className="h-4 w-4 animate-spin" />} Score my profile
        </Button>
        {!hasRole && (
          <span id="founder-form-hint" className="text-xs text-muted-foreground">Add at least one role with a title and a company.</span>
        )}
      </div>
    </form>
  )
}

export function FounderScorePanel({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const { scorecard, subject, setScorecard } = useFounderScore()
  const [tab, setTab] = useState<"samples" | "profile">("samples")
  const [samples, setSamples] = useState<SampleFounder[] | null>(null)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!isOpen || samples) return
    fetchSamples()
      .then(setSamples)
      .catch((e) => setError(friendly(e)))
  }, [isOpen, samples])

  if (!isOpen) return null

  const pick = async (id: string) => {
    setLoadingId(id)
    setError(null)
    try {
      setScorecard(await fetchSampleScore(id), { kind: "sample", id })
    } catch (e) {
      setError(friendly(e))
    } finally {
      setLoadingId(null)
    }
  }

  return (
    <div role="dialog" aria-label="Founder score" data-testid="founder-score-panel" className="fixed inset-y-0 right-0 z-[60] flex w-full flex-col border-l border-border bg-background shadow-2xl md:w-[680px] lg:w-[860px]">
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-secondary/30 px-4">
        <div className="flex items-center gap-2">
          {scorecard && (
            <Button variant="ghost" size="icon" aria-label="Back to founders" onClick={() => setScorecard(null, null)}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold">Founder score <OfflineChip /></h3>
            <p className="text-xs text-muted-foreground">Seen greatness, horsepower, domain fit, sacrifice</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close founder score">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">
        {error && (
          <p role="alert" className="mb-4 flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" /> {error}
          </p>
        )}
        {scorecard ? (
          <FounderScorecardView card={scorecard} key={subject?.kind === "sample" ? subject.id : "profile"} />
        ) : (
          <>
            <div
              role="tablist"
              aria-label="Who to score"
              className="mb-4 inline-flex rounded-lg border border-border p-0.5"
              onKeyDown={(e) => {
                if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return
                const next = tab === "samples" ? "profile" : "samples"
                setTab(next)
                document.getElementById(`founder-tab-${next}`)?.focus()
              }}
            >
              {(["samples", "profile"] as const).map((t) => (
                <button
                  key={t}
                  id={`founder-tab-${t}`}
                  role="tab"
                  aria-selected={tab === t}
                  aria-controls={`founder-tabpanel-${t}`}
                  tabIndex={tab === t ? 0 : -1}
                  onClick={() => setTab(t)}
                  className={cn("rounded-md px-3 py-1.5 text-sm", tab === t ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground")}
                >
                  {t === "samples" ? "Sample founders" : "Your profile"}
                </button>
              ))}
            </div>
            {tab === "samples" ? (
              <div className="space-y-3" role="tabpanel" id="founder-tabpanel-samples" aria-labelledby="founder-tab-samples">
                <p className="text-sm text-muted-foreground">Fictional founders, one for each recorded sample idea, to show how the score reads.</p>
                {!samples && !error && (
                  <p className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" /> Loading sample founders...
                  </p>
                )}
                {samples?.length === 0 && <p className="text-sm text-muted-foreground">No sample founders are available.</p>}
                <ul className="grid gap-3 sm:grid-cols-2">
                  {samples?.map((s) => (
                    <li key={s.id}>
                      <button
                        data-testid={`sample-${s.id}`}
                        onClick={() => pick(s.id)}
                        disabled={loadingId !== null}
                        className="flex h-full w-full flex-col gap-1 rounded-xl border border-border bg-card p-4 text-left transition-colors hover:border-primary/50 disabled:opacity-60"
                      >
                        <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                          {loadingId === s.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserRound className="h-4 w-4 text-primary" />}
                          {s.name}
                        </span>
                        <span className="text-xs text-muted-foreground">{s.current_title} at {s.company.name}</span>
                        <span className="line-clamp-2 text-xs text-foreground/80">{s.company.description}</span>
                        <span className="mt-1 w-fit rounded-full border border-border px-2 py-0.5 text-[10px] text-muted-foreground">Fictional</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div role="tabpanel" id="founder-tabpanel-profile" aria-labelledby="founder-tab-profile">
                <ProfileForm onScored={() => undefined} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
