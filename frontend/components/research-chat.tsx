"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Send, Bot, User, Loader2, Sparkles, X, AlertCircle, RotateCcw, Search } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { MarkdownReport } from "@/components/markdown-report"
import { cn } from "@/lib/utils"

interface Message {
  role: "user" | "assistant"
  content: string
  id: string
  failed?: boolean
}

interface TaskState {
  status: "queued" | "running" | "completed" | "failed" | string
  kind?: string
  provider?: string
  progress: string[]
  elapsedS?: number
}

interface ResearchChatProps {
  isOpen: boolean
  onClose: () => void
  initialContext?: {
    idea?: string
    problem?: string
    customer?: string
    product?: string
  }
}

const FIRST_MESSAGE = "Start research based on provided context."
const POLL_MS = 1500

function formatElapsed(s?: number) {
  if (s == null) return ""
  const m = Math.floor(s / 60)
  return `${m}:${Math.floor(s % 60).toString().padStart(2, "0")}`
}

// Thought summaries arrive as "**Title**\n\nBody"; split them for the log.
function splitNote(note: string) {
  const m = /^\*\*(.+?)\*\*\s*([\s\S]*)$/.exec(note.trim())
  return m ? { title: m[1], body: m[2].trim() } : { title: null, body: note }
}

function ResearchProgress({ task, firstTurn }: { task: TaskState; firstTurn: boolean }) {
  const queued = task.status === "queued"
  const notes = [...task.progress].reverse()
  return (
    <div data-testid="research-progress" role="status" aria-live="polite" className="rounded-xl border border-border bg-card p-4 md:p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="relative flex h-2.5 w-2.5">
            <span className={cn("absolute inline-flex h-full w-full rounded-full opacity-60", queued ? "bg-chart-4" : "animate-ping bg-primary")} />
            <span className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", queued ? "bg-chart-4" : "bg-primary")} />
          </span>
          <span className="text-sm font-medium text-foreground">
            {queued ? "Queued" : firstTurn ? "Researching the market" : "Looking into it"}
          </span>
        </div>
        <span className="font-mono text-xs tabular-nums text-muted-foreground">{formatElapsed(task.elapsedS)}</span>
      </div>
      <p className="mt-1.5 text-xs text-muted-foreground">
        {firstTurn
          ? task.provider === "fixture"
            ? "Offline mode: replaying a recorded deep-research run."
            : "Deep research usually takes 3 to 6 minutes. You can close this panel; it keeps going."
          : "Answering with the report as context."}
      </p>

      {notes.length > 0 && (
        <ol className="mt-4 max-h-64 space-y-3 overflow-y-auto border-l border-border pl-4" aria-label="Research log">
          {notes.map((note, i) => {
            const { title, body } = splitNote(note)
            const search = note.startsWith("Searching:")
            return (
              <li key={`${task.progress.length - i}`} className={cn("relative text-sm", i > 0 && "opacity-70")}>
                <span className={cn("absolute -left-[1.3rem] top-1.5 h-2 w-2 rounded-full border-2 border-card", i === 0 ? "bg-primary" : "bg-border")} />
                {search ? (
                  <span className="flex items-start gap-1.5 text-muted-foreground">
                    <Search className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                    <span className="line-clamp-2">{note.replace(/^Searching:\s*/, "")}</span>
                  </span>
                ) : (
                  <>
                    {title && <span className="block font-medium text-foreground">{title}</span>}
                    <span className="line-clamp-2 text-muted-foreground">{body}</span>
                  </>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

export function ResearchChat({ isOpen, onClose, initialContext }: ResearchChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [task, setTask] = useState<TaskState | null>(null)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [lastRequest, setLastRequest] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const started = useRef(false)
  const isLoading = currentTaskId !== null || task !== null

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages.length])

  const fail = useCallback((text: string) => {
    setMessages((prev) => [...prev, { role: "assistant", content: text, id: `err-${Date.now()}`, failed: true }])
    setTask(null)
    setCurrentTaskId(null)
  }, [])

  useEffect(() => {
    if (!currentTaskId) return
    let cancelled = false
    const tick = async () => {
      try {
        const res = await fetch(`/api/research?taskId=${currentTaskId}&action=status`)
        if (!res.ok) throw new Error(`status ${res.status}`)
        const data = await res.json()
        if (cancelled) return
        if (data.status === "completed") {
          setMessages((prev) => [...prev, { role: "assistant", content: data.content, id: currentTaskId }])
          setTask(null)
          setCurrentTaskId(null)
        } else if (data.status === "failed") {
          fail(data.error || "Research failed.")
        } else {
          setTask({ status: data.status, kind: data.kind, provider: data.provider, progress: data.progress ?? [], elapsedS: data.elapsed_s })
        }
      } catch (e) {
        console.error("Polling error", e)
      }
    }
    tick()
    const interval = setInterval(tick, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [currentTaskId, fail])

  const handleSendMessage = useCallback(
    async (text: string, isSystemTrigger = false) => {
      if (!text.trim()) return
      if (!isSystemTrigger) {
        setMessages((prev) => [...prev, { role: "user", content: text, id: `u-${Date.now()}` }])
      }
      setInput("")
      setLastRequest(text)
      setTask({ status: "queued", progress: [] })

      try {
        const res = await fetch("/api/research", {
          method: "POST",
          body: JSON.stringify({ message: text, session_id: sessionId, ...initialContext }),
          headers: { "Content-Type": "application/json" },
        })
        if (!res.ok) throw new Error("Failed to send message")
        const data = await res.json()
        setSessionId(data.session_id)
        setCurrentTaskId(data.task_id)
      } catch (e) {
        console.error(e)
        fail("Couldn't reach the research agent. Check that it's running on port 8000, then retry.")
      }
    },
    [fail, initialContext, sessionId]
  )

  // Start the first research turn when the panel opens with an idea.
  useEffect(() => {
    if (isOpen && !started.current && initialContext?.idea) {
      started.current = true
      handleSendMessage(FIRST_MESSAGE, true)
    }
  }, [isOpen, initialContext, handleSendMessage])

  if (!isOpen) return null

  const hasReport = messages.some((m) => m.role === "assistant" && !m.failed)
  const firstTurn = !hasReport

  return (
    <div
      data-testid="research-panel"
      role="dialog"
      aria-label="Research agent"
      className="fixed inset-y-0 right-0 z-50 flex w-full flex-col border-l border-border bg-background shadow-2xl md:w-[640px] lg:w-[820px]"
    >
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-secondary/30 px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Problem Space Specialist</h3>
            <p className="text-xs text-muted-foreground">Deep Research Agent</p>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close research panel">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto bg-muted/20 p-4 md:p-6">
        <div className="mx-auto max-w-[72ch] space-y-6">
          {messages.length === 0 && !isLoading && (
            <div className="mt-20 text-center text-muted-foreground">
              <Bot className="mx-auto mb-4 h-12 w-12 opacity-50" />
              <p className="font-medium text-foreground">No research yet</p>
              <p className="mt-1 text-sm">Enter your idea on the home page, or ask about a market below.</p>
            </div>
          )}

          {messages.map((msg) =>
            msg.role === "user" ? (
              <div key={msg.id} className="flex justify-end gap-3">
                <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">{msg.content}</div>
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <User className="h-4 w-4" />
                </div>
              </div>
            ) : msg.failed ? (
              <div key={msg.id} role="alert" className="flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                <div className="flex-1">
                  <p className="font-medium text-foreground">Research didn&apos;t finish</p>
                  <p className="mt-0.5 text-muted-foreground">{msg.content}</p>
                </div>
                {lastRequest && (
                  <Button variant="outline" size="sm" className="gap-1.5" disabled={isLoading} onClick={() => handleSendMessage(lastRequest, lastRequest === FIRST_MESSAGE)}>
                    <RotateCcw className="h-3.5 w-3.5" /> Retry
                  </Button>
                )}
              </div>
            ) : (
              <article key={msg.id} data-testid="research-report" className="rounded-xl border border-border bg-card p-5 md:p-7">
                <MarkdownReport content={msg.content} idPrefix={`m${msg.id.replace(/\W/g, "")}`} variant={msg.content.length > 3000 ? "report" : "compact"} />
              </article>
            )
          )}

          {task && <ResearchProgress task={task} firstTurn={firstTurn} />}
          <div ref={scrollRef} className="h-2" />
        </div>
      </div>

      <div className="shrink-0 border-t border-border bg-background p-3 md:p-4">
        <form onSubmit={(e) => { e.preventDefault(); handleSendMessage(input) }} className="mx-auto flex max-w-[72ch] gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={hasReport ? "Ask a follow-up about the report..." : "Ask about a market, competitor, or problem..."}
            aria-label="Message the research agent"
            disabled={isLoading}
            className="flex-1"
          />
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()} aria-label="Send">
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </form>
      </div>
    </div>
  )
}
