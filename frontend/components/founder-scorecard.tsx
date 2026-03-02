"use client"

import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts"
import { BadgeCheck, ChevronRight, CircleDashed, CircleMinus, Info, Lightbulb } from "lucide-react"
import type { Scorecard, Signal, TagSource } from "@/lib/founder-score"
import { cn } from "@/lib/utils"

// One series, one hue: the theme's chart-2 green passes the mark checks on the card surface
// (the darker primary is kept for text). Timing isn't summed, so it's off the radar and its bar is
// hatched in the same green instead of a second, low-contrast hue.
const MARK = "#3e8343"
const HATCH = `repeating-linear-gradient(135deg, ${MARK} 0 3px, transparent 3px 6px)`

const BAND = {
  strong: { icon: BadgeCheck, text: "text-primary", ring: "border-primary/30 bg-primary/5" },
  secondary: { icon: CircleDashed, text: "text-foreground", ring: "border-chart-4 bg-chart-5/30" },
  filter: { icon: CircleMinus, text: "text-muted-foreground", ring: "border-border bg-muted/40" },
} as const

const SOURCE_LABEL: Record<TagSource, string> = {
  gemini: "Gemini",
  recorded: "recorded Gemini tags",
  keyword: "keyword lexicon",
  fallback_error: "keyword lexicon (Gemini call failed)",
}

// Up to two decimals, no trailing zeros: 85.95 stays 85.95 rather than rounding to 86.0.
function fmt(n: number) {
  return String(Number(n.toFixed(2)))
}

function RadarTooltip({ active, payload }: { active?: boolean; payload?: { payload: { label: string; score: number; max: number; percent: number; summed: boolean } }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-foreground">{d.label}</p>
      <p className="text-muted-foreground">
        {fmt(d.score)} of {d.max} ({Math.round(d.percent)}%){d.summed ? "" : ", not in the composite"}
      </p>
    </div>
  )
}

function SignalRadar({ signals, describedBy }: { signals: Signal[]; describedBy: string }) {
  const data = signals
    .filter((s) => s.in_composite)
    .map((s) => ({ label: s.label, percent: s.percent, score: s.score, max: s.max, summed: true, scored: s.scored }))
  const timing = signals.find((s) => !s.in_composite)
  return (
    <figure data-testid="founder-radar" aria-label="The four composite signals, each as a percent of its maximum" aria-describedby={describedBy}>
      <div className="h-64 w-full">
        <ResponsiveContainer>
          <RadarChart data={data} outerRadius="68%" margin={{ top: 24, right: 24, bottom: 8, left: 24 }}>
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis
              dataKey="label"
              tick={({ payload, x, y, textAnchor, index }) => {
                const item = data.find((d) => d.label === payload.value)
                // The top axis label sits above its vertex instead of on it.
                const lift = index === 0 ? -20 : 0
                return (
                  <text x={x} y={y} textAnchor={textAnchor} className="fill-muted-foreground text-[11px]">
                    <tspan x={x} dy={lift}>{payload.value}</tspan>
                    <tspan x={x} dy="13" className="fill-foreground font-medium">
                      {item ? (item.scored ? `${fmt(item.score)}/${item.max}` : "not scored") : ""}
                    </tspan>
                  </text>
                )
              }}
            />
            <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} tickCount={5} />
            <Radar dataKey="percent" stroke={MARK} strokeWidth={2} fill={MARK} fillOpacity={0.14} dot={{ r: 4, fill: MARK, strokeWidth: 2, stroke: "var(--card)" }} isAnimationActive={false} />
            <Tooltip content={<RadarTooltip />} position={{ x: 8, y: 8 }} wrapperStyle={{ pointerEvents: "none" }} cursor={false} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="text-center text-[11px] text-muted-foreground">Each axis is a composite signal as a percent of its maximum.</figcaption>
      {timing && (
        <p data-testid="founder-timing-stat" className="mt-2 text-center text-xs text-muted-foreground">
          Timing (not in the composite):{" "}
          <span className="font-mono text-foreground">{timing.scored ? `${fmt(timing.score)}/${timing.max}` : "not scored"}</span>
        </p>
      )}
    </figure>
  )
}

function CompositeTrack({ score, strong, secondary }: { score: number; strong: number; secondary: number }) {
  return (
    <div className="mt-3">
      <p className="sr-only">
        Bands: below {secondary} is filter, {secondary} to {strong} is secondary, {strong} and up is strong.
      </p>
      <div className="relative h-2 overflow-hidden rounded-full" aria-hidden>
        <div className="absolute inset-y-0 left-0 bg-muted" style={{ width: `${secondary}%` }} />
        <div className="absolute inset-y-0 bg-muted/60" style={{ left: `${secondary}%`, width: `${strong - secondary}%` }} />
        <div className="absolute inset-y-0 right-0 bg-primary/10" style={{ left: `${strong}%` }} />
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${Math.min(score, 100)}%`, background: MARK }} />
      </div>
      <div className="relative h-4" aria-hidden>
        {[secondary, strong].map((t) => (
          <span key={t} className="absolute top-0 -translate-x-1/2 text-[10px] text-muted-foreground" style={{ left: `${t}%` }}>
            <span className="mx-auto block h-1.5 w-px bg-foreground/50" />
            {t === strong ? `${t} strong` : `${t} secondary`}
          </span>
        ))}
      </div>
    </div>
  )
}

function SignalRow({ signal }: { signal: Signal }) {
  return (
    <li data-testid={`signal-${signal.key}`} className="py-3">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm font-medium text-foreground">
          {signal.label}
          {!signal.in_composite && <span className="ml-2 text-xs font-normal text-muted-foreground">not in composite</span>}
          {!signal.scored && <span className="ml-2 text-xs font-normal text-muted-foreground">not scored</span>}
        </span>
        <span className="font-mono text-sm tabular-nums text-foreground">
          {signal.scored ? fmt(signal.score) : "–"}
          <span className="text-muted-foreground"> / {signal.max}</span>
        </span>
      </div>
      <div className="mt-1.5 h-1.5 rounded-full bg-muted">
        <div className="h-full rounded-full" style={{ width: `${signal.percent}%`, background: signal.in_composite ? MARK : HATCH, minWidth: signal.score > 0 ? 4 : 0 }} />
      </div>
      <details className="group mt-2" open={signal.in_composite && signal.key === "seen_greatness"}>
        <summary className="flex cursor-pointer select-none list-none items-center gap-1 text-xs text-foreground/80 hover:text-foreground [&::-webkit-details-marker]:hidden">
          <ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" aria-hidden />
          Evidence ({signal.evidence.length})
        </summary>
        <ul className="mt-2 space-y-1.5 border-l-2 border-border pl-3" data-testid="signal-evidence">
          {signal.evidence.map((e, i) => (
            <li key={i} className="text-xs leading-relaxed text-foreground/85">
              <span className="mr-1.5 rounded bg-secondary px-1 py-px font-mono text-[10px] uppercase text-secondary-foreground">{e.source}</span>
              {e.text}
            </li>
          ))}
        </ul>
      </details>
    </li>
  )
}

export function FounderScorecardView({ card }: { card: Scorecard }) {
  const band = BAND[card.composite.band]
  const BandIcon = band.icon
  const sources = [card.classifier.founder_source, card.classifier.company_source].filter(Boolean) as TagSource[]
  return (
    <article data-testid="founder-scorecard" className="space-y-5">
      <header className="flex flex-wrap items-center gap-2">
        <h3 className="font-serif text-xl font-semibold text-foreground">{card.founder.name}</h3>
        {card.founder.synthetic && (
          <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground" data-testid="synthetic-badge">
            Fictional sample founder
          </span>
        )}
        {card.company && <span className="text-sm text-muted-foreground">building {card.company.name}</span>}
      </header>

      <section className={cn("rounded-xl border p-4", band.ring)} data-testid="founder-composite">
        <div className="flex flex-wrap items-end justify-between gap-x-4 gap-y-1">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Composite</p>
            <p className="whitespace-nowrap font-serif text-4xl font-semibold tabular-nums text-foreground">
              {fmt(card.composite.score)}
              <span className="text-lg text-muted-foreground"> / 100</span>
            </p>
          </div>
          <p className={cn("flex items-center gap-1.5 text-sm font-medium", band.text)}>
            <BandIcon className="h-4 w-4" aria-hidden />
            {card.composite.label}
          </p>
        </div>
        <CompositeTrack score={card.composite.score} strong={card.composite.thresholds.strong} secondary={card.composite.thresholds.secondary} />
        <p className="mt-1 text-xs text-muted-foreground">Seen greatness + horsepower + domain fit + sacrifice, each capped.</p>
      </section>

      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <div className="rounded-xl border border-border bg-card p-3">
          <SignalRadar signals={card.signals} describedBy="founder-signal-list" />
        </div>
        <ul id="founder-signal-list" className="divide-y divide-border rounded-xl border border-border bg-card px-4">
          {card.signals.map((s) => (
            <SignalRow key={s.key} signal={s} />
          ))}
        </ul>
      </div>

      {card.advice.length > 0 && (
        <section className="rounded-xl border border-border bg-card p-4" data-testid="founder-advice">
          <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <Lightbulb className="h-4 w-4 text-primary" aria-hidden /> What to work on
          </h4>
          <ul className="space-y-1.5 text-sm text-foreground/85">
            {card.advice.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ul>
        </section>
      )}

      <footer className="flex items-start gap-2 text-[11px] leading-relaxed text-muted-foreground" data-testid="founder-provenance">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        <span>
          Heuristic score from the {card.engine} engine, as of {card.as_of}. Domain tags:{" "}
          {Array.from(new Set(sources.map((s) => SOURCE_LABEL[s]))).join(" and ") || "none"}
          {card.tags.founder.recorded_at ? ` (recorded ${card.tags.founder.recorded_at.slice(0, 10)})` : ""}. It reads a resume, not a person;
          use it to see what investors will notice first.
        </span>
      </footer>
    </article>
  )
}
