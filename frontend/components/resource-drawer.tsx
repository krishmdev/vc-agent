"use client"

import { useState, useEffect, useRef } from "react"
import { useAppStore } from "@/lib/store"
import { sequoiaResources } from "@/lib/dashboard-data"
import { cn } from "@/lib/utils"
import { OfflineChip } from "@/components/offline-chip"
import {
  X,
  BookOpen,
  Video,
  Bot,
  ExternalLink,
  Send,
  Loader2,
  MessageSquare,
  Sparkles,
  PlayCircle,
  Maximize2,
  Minimize2
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { MarkdownReport } from "@/components/markdown-report"
import { OFFLINE } from "@/lib/mode"

interface KbCitation {
  n: number
  source: string
  type: string
  url: string | null
  snippet: string
}

interface StoredGuide {
  content: string
  citations: KbCitation[]
}

// Guides cite retrieved passages as [1], [2]; MarkdownReport links "[cite: n]" markers.
const toCiteMarkers = (text: string) => text.replace(/\[(\d+(?:\s*,\s*\d+)*)\](?!\()/g, "[cite: $1]")

// Storage key for persisting generated guides
const GUIDES_STORAGE_KEY = 'sequoia-ai-guides'

// Helper to load guides from localStorage (older entries are plain strings)
const loadStoredGuides = (): Record<string, StoredGuide | string> => {
  try {
    const stored = localStorage.getItem(GUIDES_STORAGE_KEY)
    return stored ? JSON.parse(stored) : {}
  } catch {
    return {}
  }
}

// Helper to save guide to localStorage
const saveGuide = (questionId: string, content: StoredGuide) => {
  try {
    const guides = loadStoredGuides()
    guides[questionId] = content
    localStorage.setItem(GUIDES_STORAGE_KEY, JSON.stringify(guides))
  } catch (e) {
    console.error('Failed to save guide:', e)
  }
}

export function ResourceDrawer() {
  const {
    resourceSidebarOpen,
    toggleResourceSidebar,
    activeResourceQuestionId,
    modules,
    activeModuleId,
    expandedModuleId
  } = useAppStore()

  const [aiArticle, setAiArticle] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [chatMessage, setChatMessage] = useState("")
  const [citations, setCitations] = useState<KbCitation[]>([])
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "model"; content: string; citations?: KbCitation[] }[]>([])
  const [isChatting, setIsChatting] = useState(false)
  const [showAiSection, setShowAiSection] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isExpanded, setIsExpanded] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Identify the relevant module and question
  const currentModuleId = expandedModuleId || activeModuleId
  const currentQuestion = currentModuleId && activeResourceQuestionId
    ? modules[currentModuleId]?.subsections
        .flatMap(s => s.questions)
        .find(q => q.id === activeResourceQuestionId)
    : null

  // Filter resources
  const relevantResources = currentModuleId
    ? sequoiaResources.filter(r => r.moduleId === currentModuleId)
    : []

  const displayedResources = activeResourceQuestionId
    ? relevantResources.filter(
        r => !r.questionIds || r.questionIds.includes(activeResourceQuestionId)
      )
    : relevantResources

  // Separate video vs text resources - strict filtering
  const articles = displayedResources.filter(r => !r.videoUrl || r.videoUrl.trim() === "")

  // Videos: EXTREMELY strict - only show if BOTH conditions are met:
  // 1. Has a valid videoUrl
  // 2. Has questionIds array that includes the EXACT current question
  const videos = activeResourceQuestionId
    ? displayedResources.filter(r => {
        // Must have valid video URL
        if (!r.videoUrl || r.videoUrl.trim() === "") return false
        // Must have questionIds array
        if (!r.questionIds || !Array.isArray(r.questionIds)) return false
        // Must include the exact current question
        return r.questionIds.includes(activeResourceQuestionId)
      })
    : [] // No videos if no specific question selected

  // Auto-scroll chat to bottom
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatHistory, isChatting])

  // Effect: Load stored guide when question changes
  useEffect(() => {
    if (resourceSidebarOpen && activeResourceQuestionId) {
      setChatHistory([])
      setError(null)

      // Try to load previously generated guide from localStorage
      const storedGuides = loadStoredGuides()
      const storedGuide = storedGuides[activeResourceQuestionId]

      if (storedGuide) {
        const guide = typeof storedGuide === "string" ? { content: storedGuide, citations: [] } : storedGuide
        setAiArticle(guide.content)
        setCitations(guide.citations)
        setShowAiSection(true)
      } else {
        setAiArticle(null)
        setCitations([])
        setShowAiSection(false)
      }
    }
  }, [activeResourceQuestionId, resourceSidebarOpen])

  const generateAiGuide = async () => {
    if (!currentQuestion || !currentModuleId) return

    setIsGenerating(true)
    setError(null)
    try {
      const response = await fetch("/api/resource-article", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: currentQuestion.label,
          module: currentModuleId,
          context: "Early stage startup validation"
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to generate" }))
        throw new Error(errorData.detail || "Failed to generate guide")
      }

      const data = await response.json()

      if (!data?.content) {
        throw new Error("No content received from server")
      }

      setAiArticle(data.content)
      setCitations(data.citations ?? [])
      setShowAiSection(true)

      // Save to localStorage for persistence
      if (activeResourceQuestionId) {
        saveGuide(activeResourceQuestionId, { content: data.content, citations: data.citations ?? [] })
      }
    } catch (e) {
      console.error("Error generating guide:", e)
      setError(e instanceof Error ? e.message : "Failed to generate guide. Please try again.")
    } finally {
      setIsGenerating(false)
    }
  }

  const sendChatMessage = async () => {
    if (!chatMessage.trim() || !aiArticle) return

    const userMsg = chatMessage
    setChatMessage("")
    setChatHistory(prev => [...prev, { role: "user", content: userMsg }])
    setIsChatting(true)
    setError(null)

    try {
      const response = await fetch("/api/resource-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg,
          history: chatHistory.map(({ role, content }) => ({ role, content })),
          resource_context: aiArticle
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to get response" }))
        throw new Error(errorData.detail || "Failed to get response")
      }

      const data = await response.json()

      if (!data?.message) {
        throw new Error("No response received from server")
      }

      setChatHistory(prev => [...prev, { role: "model", content: data.message, citations: data.citations ?? [] }])
    } catch (e) {
      console.error("Error in chat:", e)
      setError(e instanceof Error ? e.message : "Failed to send message. Please try again.")
      // Remove the user message we just added since it failed
      setChatHistory(prev => prev.slice(0, -1))
    } finally {
      setIsChatting(false)
    }
  }

  if (!resourceSidebarOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 transition-opacity"
        onClick={() => toggleResourceSidebar(false)}
      />

      {/* Drawer */}
      <div className={cn(
        "fixed inset-y-0 right-0 z-50 bg-background border-l border-border shadow-2xl flex flex-col animate-in slide-in-from-right duration-300 transition-all",
        isExpanded ? "w-full lg:w-[90%]" : "w-full sm:w-[540px]"
      )}>

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <BookOpen className="w-4 h-4 text-primary" />
            </div>
            <div>
              <h2 className="flex items-center gap-2 font-semibold text-sm">Sequoia Knowledge Base <OfflineChip /></h2>
              {currentQuestion && (
                <p className="text-xs text-muted-foreground truncate max-w-[300px]">
                  {currentQuestion.label}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsExpanded(!isExpanded)}
              title={isExpanded ? "Minimize" : "Expand"}
            >
              {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </Button>
            <Button variant="ghost" size="icon" onClick={() => toggleResourceSidebar(false)}>
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Unified Content Area */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-6 space-y-8">

            {/* Error Display */}
            {error && (
              <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive text-sm">
                {error}
              </div>
            )}

            {/* Articles Section */}
            {articles.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <BookOpen className="w-4 h-4 text-primary" />
                  <h3 className="text-base font-semibold">Recommended Reading</h3>
                  <span className="text-xs text-muted-foreground">({articles.length})</span>
                </div>
                <div className="space-y-3">
                  {articles.map(resource => (
                    <a
                      key={resource.id}
                      href={resource.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block group"
                    >
                      <div className="p-4 rounded-xl border border-border bg-card hover:border-primary/50 hover:shadow-md transition-all">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <h4 className="font-medium text-sm group-hover:text-primary transition-colors mb-1">
                              {resource.title}
                            </h4>
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {resource.description}
                            </p>
                          </div>
                          <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0 mt-1" />
                        </div>
                      </div>
                    </a>
                  ))}
                </div>
              </section>
            )}

            {/* Videos Section - Only show if videos exist */}
            {videos.length > 0 && (
              <section>
                <div className="flex items-center gap-2 mb-4">
                  <Video className="w-4 h-4 text-primary" />
                  <h3 className="text-base font-semibold">Masterclass Videos</h3>
                  <span className="text-xs text-muted-foreground">({videos.length})</span>
                </div>
                <div className="space-y-6">
                  {videos.map(resource => (
                    <div key={resource.id} className="space-y-3">
                      <div className="aspect-video rounded-xl overflow-hidden bg-muted border border-border shadow-sm">
                        {resource.videoUrl ? (
                          <iframe
                            src={resource.videoUrl}
                            title={resource.title}
                            className="w-full h-full"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                            <PlayCircle className="w-12 h-12" />
                          </div>
                        )}
                      </div>
                      <div>
                        <h4 className="font-medium text-sm mb-1">{resource.title}</h4>
                        <p className="text-xs text-muted-foreground">{resource.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* AI Partner Section */}
            <section>
              <div className="flex items-center gap-2 mb-4">
                <Bot className="w-4 h-4 text-primary" />
                <h3 className="text-base font-semibold">AI Partner</h3>
              </div>

              {!showAiSection ? (
                <div className="p-6 rounded-xl border border-border bg-card space-y-4 text-center">
                  <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                    <Sparkles className="w-6 h-6 text-primary" />
                  </div>
                  <div className="space-y-2">
                    <h4 className="font-semibold">Generate Tactical Guide</h4>
                    <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                      Create a custom Sequoia-style guide for &ldquo;{currentQuestion?.label || 'this topic'}&rdquo;
                    </p>
                  </div>
                  <Button onClick={generateAiGuide} disabled={isGenerating} className="mx-auto">
                    {isGenerating ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Researching...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-4 h-4 mr-2" />
                        Generate Guide
                      </>
                    )}
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* AI Generated Article */}
                  <div className="p-6 rounded-xl border border-primary/20 bg-primary/5">
                    <div className="flex items-center justify-between mb-4 pb-4 border-b border-border/50">
                      <span className="text-xs font-medium text-primary bg-primary/10 px-3 py-1 rounded-full">
                        AI Generated Resource
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={generateAiGuide}
                        disabled={isGenerating}
                        className="h-7 text-xs"
                      >
                        {isGenerating ? (
                          <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                        ) : null}
                        Regenerate
                      </Button>
                    </div>
                    <div data-testid="kb-guide" className="text-sm">
                      <MarkdownReport content={toCiteMarkers(aiArticle || "")} variant="compact" idPrefix="kb" />
                    </div>
                  </div>

                  {citations.length > 0 && <KbSources citations={citations} idPrefix="kb" />}

                  {/* Chat History */}
                  {chatHistory.length > 0 && (
                    <div className="space-y-3">
                      <div className="flex items-center gap-2 text-xs font-semibold uppercase text-muted-foreground">
                        <MessageSquare className="w-3 h-3" />
                        Discussion
                      </div>
                      {chatHistory.map((msg, i) => (
                        <div key={i} className={cn(
                          "flex gap-3",
                          msg.role === "user" ? "justify-end" : "justify-start"
                        )}>
                          <div className={cn(
                            "px-4 py-2 rounded-2xl max-w-[85%] text-sm",
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground rounded-tr-none"
                              : "bg-muted text-foreground rounded-tl-none"
                          )}>
                            {msg.role === "user" ? msg.content : (
                              <>
                                <MarkdownReport content={toCiteMarkers(msg.content)} variant="compact" idPrefix={`kbc${i}`} className="[&_p:last-child]:mb-0" />
                                {msg.citations && msg.citations.length > 0 && <KbSources citations={msg.citations} idPrefix={`kbc${i}`} dense />}
                              </>
                            )}
                          </div>
                        </div>
                      ))}
                      {isChatting && (
                        <div className="flex gap-3 justify-start">
                          <div className="bg-muted px-4 py-2 rounded-2xl rounded-tl-none">
                            <Loader2 className="w-4 h-4 animate-spin" />
                          </div>
                        </div>
                      )}
                      <div ref={chatEndRef} />
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* Empty State */}
            {articles.length === 0 && videos.length === 0 && !showAiSection && (
              <div className="text-center py-12 text-muted-foreground">
                <Sparkles className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p className="mb-4">No curated resources found for this section.</p>
                <Button variant="outline" onClick={generateAiGuide} disabled={isGenerating}>
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Bot className="w-4 h-4 mr-2" />
                      Generate AI Guide
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Chat Input (Sticky at bottom when AI article exists) */}
        {showAiSection && aiArticle && (
          <div className="p-4 border-t border-border bg-background">
            <form
              onSubmit={(e) => { e.preventDefault(); sendChatMessage(); }}
              className="flex items-center gap-2"
            >
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  placeholder="Ask a follow-up question..."
                  className="w-full px-4 py-2.5 rounded-full border border-border bg-muted/50 focus:outline-none focus:ring-2 focus:ring-primary/50 text-sm"
                  disabled={isChatting}
                />
              </div>
              <Button
                type="submit"
                size="icon"
                className="h-10 w-10 rounded-full shrink-0"
                disabled={!chatMessage.trim() || isChatting}
              >
                {isChatting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </form>
          </div>
        )}
      </div>
    </>
  )
}

function KbSources({ citations, idPrefix, dense }: { citations: KbCitation[]; idPrefix: string; dense?: boolean }) {
  return (
    <section data-testid="kb-sources" aria-label="Sources from the Sequoia knowledge base" className={cn(dense ? "mt-3" : "rounded-xl border border-border bg-card p-4")}>
      <h4 className="mb-2.5 flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        <span>Sequoia knowledge base</span>
        {!dense && OFFLINE && <span className="normal-case tracking-normal font-normal">local MiniLM index</span>}
      </h4>
      <ol className="space-y-2">
        {citations.map((c) => (
          <li key={c.n} id={`${idPrefix}-src-${c.n}`} className="flex scroll-mt-20 gap-2.5 rounded-lg p-1 target:bg-primary/10">
            <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-primary/10 font-mono text-[0.7rem] font-medium text-primary">{c.n}</span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline gap-2">
                {c.url ? (
                  <a href={c.url} target="_blank" rel="noopener noreferrer" className="truncate text-sm font-medium text-foreground hover:text-primary">{c.source}</a>
                ) : (
                  <span className="truncate text-sm font-medium text-foreground">{c.source}</span>
                )}
                <span className="shrink-0 text-[0.7rem] text-muted-foreground">{c.type === "website" ? "sequoiacap.com" : "Podcast transcript"}</span>
              </div>
              {!dense && <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{c.snippet}</p>}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
