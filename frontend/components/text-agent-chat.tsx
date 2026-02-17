"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { AlertCircle, BookOpen, Brain, Loader2, RotateCcw, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { AGENT_WS_URL } from "@/lib/mode"
import { cn } from "@/lib/utils"

type Mode = "mentor" | "vc"

interface Citation {
  source: string
  url: string | null
}

interface ChatTurn {
  id: string
  role: "founder" | "agent"
  text: string
  citations?: Citation[]
  tools?: { name: string }[]
  memories?: string[]
}

interface TextAgentChatProps {
  mode: Mode
  idea?: string
  className?: string
  compact?: boolean
  // VC mode: called with the post-call report once the agent has written it.
  onReport?: (report: Record<string, unknown> | null) => void
  reportRequested?: boolean
}

type Status = "connecting" | "ready" | "waiting" | "error" | "closed"

const LABELS: Record<Mode, { agent: string; placeholder: string }> = {
  mentor: { agent: "Sequoia mentor", placeholder: "Tell the mentor about your idea..." },
  vc: { agent: "VC partner", placeholder: "Make your pitch..." },
}

function dedupe(citations: Citation[] = []) {
  const seen = new Set<string>()
  return citations.filter((c) => (seen.has(c.source) ? false : (seen.add(c.source), true)))
}

export function TextAgentChat({ mode, idea, className, compact, onReport, reportRequested }: TextAgentChatProps) {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [status, setStatus] = useState<Status>("connecting")
  const [error, setError] = useState<string | null>(null)
  const [input, setInput] = useState("")
  const [attempt, setAttempt] = useState(0)
  const ws = useRef<WebSocket | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const onReportRef = useRef(onReport)
  useEffect(() => {
    onReportRef.current = onReport
  }, [onReport])

  useEffect(() => {
    const params = new URLSearchParams({ mode })
    if (idea) params.set("idea", idea)
    const socket = new WebSocket(`${AGENT_WS_URL}/ws/chat?${params.toString()}`)
    ws.current = socket
    setStatus("connecting")
    setError(null)

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === "agent_message") {
        setTurns((prev) => [
          ...prev,
          { id: `a-${prev.length}`, role: "agent", text: msg.text, citations: msg.citations, tools: msg.tools, memories: msg.memories },
        ])
        setStatus("ready")
      } else if (msg.type === "vc_report") {
        onReportRef.current?.(msg.data ?? null)
        setStatus("ready")
      } else if (msg.type === "error") {
        setError(msg.message)
        setStatus("error")
      }
    }
    socket.onerror = () => {
      setError("Couldn't reach the mentor service on port 8001.")
      setStatus("error")
    }
    socket.onclose = () => setStatus((s) => (s === "error" ? s : "closed"))
    return () => socket.close()
  }, [mode, idea, attempt])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [turns.length, status])

  useEffect(() => {
    if (status === "ready") inputRef.current?.focus()
  }, [status])

  useEffect(() => {
    if (reportRequested && ws.current?.readyState === WebSocket.OPEN) {
      setStatus("waiting")
      ws.current.send(JSON.stringify({ type: "generate_report" }))
    }
  }, [reportRequested])

  const send = useCallback(() => {
    const text = input.trim()
    if (!text || status !== "ready" || !ws.current) return
    setTurns((prev) => [...prev, { id: `f-${prev.length}`, role: "founder", text }])
    ws.current.send(JSON.stringify({ type: "user_message", text }))
    setInput("")
    setStatus("waiting")
  }, [input, status])

  const { agent, placeholder } = LABELS[mode]

  return (
    <div data-testid={`text-chat-${mode}`} className={cn("flex min-h-0 flex-col overflow-hidden rounded-2xl border border-border bg-card", className)}>
      <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className={cn("h-2 w-2 rounded-full", status === "error" ? "bg-destructive" : status === "connecting" ? "bg-chart-4" : "bg-primary")} />
          <span className="text-sm font-medium">{agent}</span>
        </div>
        <span className="rounded-full bg-secondary px-2 py-0.5 text-[0.7rem] font-medium text-secondary-foreground" title="NEXT_PUBLIC_VC_AGENT_MODE=offline: text transport with a scripted model">
          Offline text mode
        </span>
      </div>

      <div className={cn("min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-4", compact ? "text-sm" : "text-[0.95rem]")} aria-live="polite">
        {status === "connecting" && turns.length === 0 && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Connecting to the {agent.toLowerCase()}...
          </p>
        )}

        {turns.map((turn) =>
          turn.role === "founder" ? (
            <div key={turn.id} className="flex justify-end">
              <p className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-3.5 py-2 text-primary-foreground">{turn.text}</p>
            </div>
          ) : (
            <div key={turn.id} data-testid="agent-turn" className="max-w-[92%] space-y-2">
              <p className="font-serif leading-relaxed text-foreground">{turn.text}</p>

              {turn.memories && turn.memories.length > 0 && (
                <div data-testid="recalled-memories" className="rounded-lg border-l-2 border-chart-4 bg-secondary/60 px-3 py-2">
                  <p className="mb-1 flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wide text-muted-foreground">
                    <Brain className="h-3 w-3" aria-hidden /> Recalled from memory
                  </p>
                  <ul className="space-y-0.5 text-sm text-foreground/85">
                    {turn.memories.map((m) => (
                      <li key={m}>&ldquo;{m}&rdquo;</li>
                    ))}
                  </ul>
                </div>
              )}

              {turn.citations && turn.citations.length > 0 && (
                <div data-testid="kb-citations" className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[0.7rem] font-semibold uppercase tracking-wide text-muted-foreground">Sequoia KB</span>
                  {dedupe(turn.citations).map((c) =>
                    c.url ? (
                      <a key={c.source} href={c.url} target="_blank" rel="noopener noreferrer" className="source-tag hover:border-primary/40">
                        <BookOpen className="h-3 w-3 shrink-0 text-primary" aria-hidden />
                        <span className="truncate">{c.source}</span>
                      </a>
                    ) : (
                      <span key={c.source} className="source-tag">
                        <BookOpen className="h-3 w-3 shrink-0 text-primary" aria-hidden />
                        <span className="truncate">{c.source}</span>
                      </span>
                    )
                  )}
                </div>
              )}
            </div>
          )
        )}

        {status === "waiting" && (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> {reportRequested ? "Writing your report..." : "Searching the knowledge base..."}
          </p>
        )}

        {(status === "error" || status === "closed") && (
          <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            <span className="flex-1 text-muted-foreground">{error ?? "The conversation ended."}</span>
            <Button variant="outline" size="sm" className="h-7 gap-1" onClick={() => { setTurns([]); setAttempt((n) => n + 1) }}>
              <RotateCcw className="h-3 w-3" /> Reconnect
            </Button>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send() }} className="flex gap-2 border-t border-border p-3">
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholder}
          aria-label={`Message the ${agent.toLowerCase()}`}
          disabled={status !== "ready"}
          className="min-w-0 flex-1 rounded-full border border-border bg-background px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 disabled:opacity-60"
        />
        <Button type="submit" size="icon" className="shrink-0 rounded-full" disabled={status !== "ready" || !input.trim()} aria-label="Send message">
          <Send className="h-4 w-4" />
        </Button>
      </form>
    </div>
  )
}
