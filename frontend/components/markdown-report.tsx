"use client"

import { useMemo } from "react"
import ReactMarkdown, { type Components } from "react-markdown"
import { ExternalLink } from "lucide-react"
import { cn } from "@/lib/utils"

interface Source {
  n: number
  label: string
  url: string
}

// Deep research writes "[cite: 3, 12]" markers and ends with a numbered "**Sources:**" list.
const CITE = /\[cite:\s*([\d,\s–-]+)\]/g
const SOURCES_HEADING = /\n\s*(?:\*\*Sources:?\*\*:?|#{1,3}\s*Sources:?)\s*\n/i
const SOURCE_LINE = /^\s*(\d+)\.\s+\[([^\]]+)\]\(([^)\s]+)\)/

function expand(list: string): number[] {
  const out: number[] = []
  for (const part of list.split(",")) {
    const [a, b] = part.split(/[–-]/).map((x) => parseInt(x.trim(), 10))
    if (Number.isNaN(a)) continue
    if (!Number.isNaN(b) && b >= a && b - a < 20) for (let i = a; i <= b; i++) out.push(i)
    else out.push(a)
  }
  return out
}

export function splitReport(content: string): { body: string; sources: Source[] } {
  const match = SOURCES_HEADING.exec(content)
  if (!match) return { body: content, sources: [] }
  const sources: Source[] = []
  for (const line of content.slice(match.index + match[0].length).split("\n")) {
    const m = SOURCE_LINE.exec(line)
    if (m) sources.push({ n: Number(m[1]), label: m[2], url: m[3] })
  }
  return { body: content.slice(0, match.index), sources }
}

function slug(text: string) {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")
}

function textOf(children: React.ReactNode): string {
  if (typeof children === "string" || typeof children === "number") return String(children)
  if (Array.isArray(children)) return children.map(textOf).join("")
  if (children && typeof children === "object" && "props" in children) {
    return textOf((children as { props: { children?: React.ReactNode } }).props.children)
  }
  return ""
}

const headingLabel = (t: string) => t.replace(/^\d+\.\s*/, "").toLowerCase().replace(/(^|\s)\S/g, (s) => s.toUpperCase())

interface MarkdownReportProps {
  content: string
  // Adds a jump bar for top-level sections and a numbered source list, for long reports.
  variant?: "report" | "compact"
  idPrefix?: string
  className?: string
}

export function MarkdownReport({ content, variant = "report", idPrefix = "r", className }: MarkdownReportProps) {
  const { body, sources, sections } = useMemo(() => {
    const { body, sources } = splitReport(content)
    const linked = body.replace(CITE, (_, list: string) =>
      expand(list).map((n) => `[${n}](#${idPrefix}-src-${n})`).join("")
    )
    const sections = variant === "report" ? [...linked.matchAll(/^# (.+)$/gm)].map((m) => m[1].trim()) : []
    return { body: linked, sources, sections }
  }, [content, idPrefix, variant])

  const components: Components = {
    h1: ({ children }) => (
      <h2
        id={`${idPrefix}-${slug(textOf(children))}`}
        className="scroll-mt-4 font-serif text-xl md:text-2xl font-semibold text-foreground mt-10 first:mt-0 mb-4 pb-2 border-b border-border"
      >
        {children}
      </h2>
    ),
    h2: ({ children }) => <h3 className="font-serif text-lg font-semibold text-primary mt-7 mb-2">{children}</h3>,
    h3: ({ children }) => <h4 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mt-6 mb-2">{children}</h4>,
    p: ({ children }) => <p className="mb-4 leading-7 text-foreground/90">{children}</p>,
    ul: ({ children }) => <ul className="list-disc pl-5 mb-4 space-y-1.5 marker:text-primary/60">{children}</ul>,
    ol: ({ children }) => <ol className="list-decimal pl-5 mb-4 space-y-1.5 marker:text-muted-foreground">{children}</ol>,
    li: ({ children }) => <li className="leading-7 text-foreground/90 pl-1">{children}</li>,
    strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
    hr: () => <hr className="my-8 border-border" />,
    blockquote: ({ children }) => (
      <div className="mb-6 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 text-sm text-muted-foreground [&_p]:mb-0 [&_p]:text-muted-foreground">
        {children}
      </div>
    ),
    code: ({ children }) => <code className="rounded bg-muted px-1 py-0.5 font-mono text-[0.85em]">{children}</code>,
    a: ({ href, children }) => {
      if (href?.startsWith(`#${idPrefix}-src-`)) {
        return (
          <a
            href={href}
            className="cite-chip"
            aria-label={`Source ${textOf(children)}`}
          >
            {children}
          </a>
        )
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer" className="font-medium text-primary underline decoration-primary/30 underline-offset-2 hover:decoration-primary">
          {children}
        </a>
      )
    },
  }

  return (
    <div className={cn("text-[0.95rem]", className)}>
      {sections.length > 1 && (
        <nav aria-label="Report sections" className="sticky -top-4 z-10 -mx-5 mb-6 flex gap-1.5 overflow-x-auto border-b border-border bg-card px-5 py-2.5 md:-top-6 md:-mx-7 md:px-7">
          {sections.map((s) => (
            <a
              key={s}
              href={`#${idPrefix}-${slug(s)}`}
              className="shrink-0 rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground hover:border-primary/40 hover:text-foreground"
            >
              {headingLabel(s)}
            </a>
          ))}
          {sources.length > 0 && (
            <a href={`#${idPrefix}-sources`} className="shrink-0 rounded-full border border-border px-3 py-1 text-xs font-medium text-muted-foreground hover:border-primary/40 hover:text-foreground">
              Sources ({sources.length})
            </a>
          )}
        </nav>
      )}

      <ReactMarkdown components={components}>{body}</ReactMarkdown>

      {sources.length > 0 && (
        <section id={`${idPrefix}-sources`} className="scroll-mt-4 mt-10 border-t border-border pt-5">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Sources</h2>
          <ol className="grid gap-x-6 gap-y-1.5 sm:grid-cols-2">
            {sources.map((s) => (
              <li key={s.n} id={`${idPrefix}-src-${s.n}`} className="flex scroll-mt-16 items-baseline gap-2 text-sm target:rounded target:bg-primary/10">
                <span className="w-6 shrink-0 text-right font-mono text-xs text-muted-foreground">{s.n}</span>
                <a href={s.url} target="_blank" rel="noopener noreferrer" className="flex min-w-0 items-center gap-1 text-foreground/80 hover:text-primary">
                  <span className="truncate">{s.label}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 opacity-50" aria-hidden />
                </a>
              </li>
            ))}
          </ol>
        </section>
      )}
    </div>
  )
}
