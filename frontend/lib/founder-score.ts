import { create } from "zustand"
import { OFFLINE } from "@/lib/mode"

// Mirrors research-agent/founder_api.py's Scorecard.
export type SignalKey = "seen_greatness" | "horsepower" | "domain_fit" | "sacrifice" | "timing"
export type TagSource = "gemini" | "recorded" | "keyword" | "fallback_error"

export interface Evidence {
  text: string
  source: "registry" | "profile" | "classifier" | "rule"
  points: number | null
}

export interface Signal {
  key: SignalKey
  label: string
  score: number
  max: number
  percent: number
  in_composite: boolean
  scored: boolean
  evidence: Evidence[]
}

export interface DomainTags {
  primary_domain: string
  primary_subdomain: string
  source: TagSource
  model?: string | null
  recorded_at?: string | null
  error?: string | null
}

export interface CompanyInput {
  name: string
  description?: string
  industry?: string
  raise_amount?: number | null
  raise_date?: string | null
}

export interface Scorecard {
  engine: string
  classifier: { name: string; founder_source?: TagSource | null; company_source?: TagSource | null }
  as_of: string
  founder: { name: string; synthetic: boolean }
  company: CompanyInput | null
  composite: {
    score: number
    max: number
    band: "strong" | "secondary" | "filter"
    label: string
    thresholds: { strong: number; secondary: number }
  }
  signals: Signal[]
  advice: string[]
  tags: { founder: DomainTags; company: DomainTags | null }
}

export interface SampleFounder {
  id: string
  name: string
  current_title: string | null
  company: CompanyInput
  synthetic: true
  note: string
}

export interface ExperienceInput {
  company: string
  title: string
  start_date?: string
  end_date?: string
}

export interface ProfileInput {
  name: string
  current_title?: string
  experience: ExperienceInput[]
  education: { school: string; degree: string; major: string }[]
}

// Kept apart from the persisted app store: a scorecard is a view of one request, and sample
// founders are fictional, so neither belongs in the founder's saved profile.
interface FounderScoreState {
  scorecard: Scorecard | null
  subject: { kind: "sample"; id: string } | { kind: "profile" } | null
  setScorecard: (scorecard: Scorecard | null, subject: FounderScoreState["subject"]) => void
}

export const useFounderScore = create<FounderScoreState>()((set) => ({
  scorecard: null,
  subject: null,
  setScorecard: (scorecard, subject) => set({ scorecard, subject }),
}))

async function readJson<T>(res: Response): Promise<T> {
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = (data as { detail?: unknown }).detail
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`)
  }
  return data as T
}

function localDate() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

export const fetchSamples = () => fetch("/api/founder-score/samples").then((r) => readJson<SampleFounder[]>(r))
export const fetchSampleScore = (id: string) =>
  fetch(`/api/founder-score/samples/${encodeURIComponent(id)}`).then((r) => readJson<Scorecard>(r))
export const scoreProfile = (profile: ProfileInput, company: CompanyInput | null) =>
  fetch("/api/founder-score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    // Live scores use the founder's date; offline mode pins it server-side for reproducibility.
    body: JSON.stringify({ profile, company, ...(OFFLINE ? {} : { as_of: localDate() }) }),
  }).then((r) => readJson<Scorecard>(r))
