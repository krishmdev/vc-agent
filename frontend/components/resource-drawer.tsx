"use client"

import { useState, useEffect, useRef } from "react"
import { useAppStore } from "@/lib/store"
import { sequoiaResources } from "@/lib/dashboard-data"
import { SequoiaResource } from "@/lib/dashboard-types"
import { cn } from "@/lib/utils"
import {
  X,
  BookOpen,
  Video,
  Bot,
  ExternalLink,
  Send,
  Loader2,
  ChevronRight,
  MessageSquare,
  Sparkles
} from "lucide-react"
import ReactMarkdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export function ResourceDrawer() {
  const {
    resourceSidebarOpen,
    toggleResourceSidebar,
    activeResourceQuestionId,
    modules,
    activeModuleId,
    expandedModuleId
  } = useAppStore()

  const [activeTab, setActiveTab] = useState<"read" | "watch" | "ask">("read")
  const [aiArticle, setAiArticle] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [chatMessage, setChatMessage] = useState("")
  const [chatHistory, setChatHistory] = useState<{ role: "user" | "model"; content: string }[]>([])
  const [isChatting, setIsChatting] = useState(false)

  // Identify the relevant module and question
  const currentModuleId = expandedModuleId || activeModuleId
  // If activeResourceQuestionId is set, find that question object to get its label
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

  // Separate video vs text resources
  const articles = displayedResources.filter(r => !r.videoUrl)
  const videos = displayedResources.filter(r => r.videoUrl)

  // Effect: When active question changes, reset AI state and potentially auto-generate
  useEffect(() => {
    if (resourceSidebarOpen && activeResourceQuestionId) {
      setAiArticle(null)
      setChatHistory([])
      // Optional: Auto-generate on open could be enabled here
      // generateAiGuide()
    }
  }, [activeResourceQuestionId, resourceSidebarOpen])

  const generateAiGuide = async () => {
    if (!currentQuestion || !currentModuleId) return

    setIsGenerating(true)
    try {
        // Construct context from other answers in the module?
        // For now, simple context
        const response = await fetch("http://localhost:8000/generate_resource_article", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: currentQuestion.label,
                module: currentModuleId,
                context: "Early stage startup validation" // Could grab more state here
            })
        })

        if (!response.ok) throw new Error("Failed to generate")

        const data = await response.json()
        setAiArticle(data.content)
        setActiveTab("ask") // Switch to AI tab to show result
    } catch (e) {
        console.error(e)
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

    try {
        const response = await fetch("http://localhost:8000/resource_chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userMsg,
                history: chatHistory,
                resource_context: aiArticle
            })
        })

        if (!response.ok) throw new Error("Failed to chat")

        const data = await response.json()
        setChatHistory(prev => [...prev, { role: "model", content: data.message }])
    } catch (e) {
        console.error(e)
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
      <div className="fixed inset-y-0 right-0 w-full sm:w-[540px] z-50 bg-background border-l border-border shadow-2xl flex flex-col animate-in slide-in-from-right duration-300">

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
            <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                    <BookOpen className="w-4 h-4 text-primary" />
                </div>
                <div>
                    <h2 className="font-semibold text-sm">Sequoia Knowledge Base</h2>
                    {currentQuestion && (
                        <p className="text-xs text-muted-foreground truncate max-w-[300px]">
                            {currentQuestion.label}
                        </p>
                    )}
                </div>
            </div>
            <Button variant="ghost" size="icon" onClick={() => toggleResourceSidebar(false)}>
                <X className="w-4 h-4" />
            </Button>
        </div>

        {/* Content Tabs */}
        <Tabs value={activeTab} onValueChange={(v: any) => setActiveTab(v)} className="flex-1 flex flex-col min-h-0">
            <div className="px-4 pt-2 border-b border-border/50">
                <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="read" className="gap-2">
                        <BookOpen className="w-3.5 h-3.5" /> Read
                    </TabsTrigger>
                    <TabsTrigger value="watch" className="gap-2">
                        <Video className="w-3.5 h-3.5" /> Watch
                    </TabsTrigger>
                    <TabsTrigger value="ask" className="gap-2">
                        <Bot className="w-3.5 h-3.5" /> AI Partner
                    </TabsTrigger>
                </TabsList>
            </div>

            {/* READ TAB */}
            <TabsContent value="read" className="flex-1 overflow-hidden data-[state=inactive]:hidden mt-0">
                <ScrollArea className="h-full p-6">
                    <div className="space-y-4">
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-semibold">Recommended Reading</h3>
                            <span className="text-xs text-muted-foreground">{articles.length} articles</span>
                        </div>

                        {articles.length === 0 ? (
                            <div className="text-center py-12 text-muted-foreground">
                                <p>No specific articles found for this section.</p>
                                <Button variant="link" onClick={() => setActiveTab("ask")}>
                                    Generate a guide instead?
                                </Button>
                            </div>
                        ) : (
                            articles.map(resource => (
                                <a
                                    key={resource.id}
                                    href={resource.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="block group"
                                >
                                    <div className="p-4 rounded-xl border border-border bg-card hover:border-primary/50 transition-all">
                                        <div className="flex items-start justify-between gap-4">
                                            <div>
                                                <h4 className="font-medium text-sm group-hover:text-primary transition-colors">
                                                    {resource.title}
                                                </h4>
                                                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                                    {resource.description}
                                                </p>
                                            </div>
                                            <ExternalLink className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0" />
                                        </div>
                                    </div>
                                </a>
                            ))
                        )}
                    </div>
                </ScrollArea>
            </TabsContent>

            {/* WATCH TAB */}
            <TabsContent value="watch" className="flex-1 overflow-hidden data-[state=inactive]:hidden mt-0">
                <ScrollArea className="h-full p-6">
                     <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <h3 className="text-lg font-semibold">Masterclass Videos</h3>
                            <span className="text-xs text-muted-foreground">{videos.length} videos</span>
                        </div>

                        {videos.length === 0 ? (
                             <div className="text-center py-12 text-muted-foreground">
                                <p>No specific videos curated for this section.</p>
                            </div>
                        ) : (
                            videos.map(resource => (
                                <div key={resource.id} className="space-y-2">
                                    <div className="aspect-video rounded-xl overflow-hidden bg-muted border border-border">
                                        {resource.videoUrl ? (
                                            <iframe
                                                src={resource.videoUrl}
                                                title={resource.title}
                                                className="w-full h-full"
                                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                                allowFullScreen
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center">
                                                <p>Video not available</p>
                                            </div>
                                        )}
                                    </div>
                                    <div>
                                        <h4 className="font-medium text-sm">{resource.title}</h4>
                                        <p className="text-xs text-muted-foreground">{resource.description}</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </ScrollArea>
            </TabsContent>

            {/* ASK (AI) TAB */}
            <TabsContent value="ask" className="flex-1 flex flex-col min-h-0 data-[state=inactive]:hidden mt-0">
                {/* Generated Content Area */}
                <ScrollArea className="flex-1 p-6">
                    {!aiArticle ? (
                        <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
                            <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                                <Sparkles className="w-6 h-6 text-primary" />
                            </div>
                            <div className="space-y-2 max-w-sm">
                                <h3 className="font-semibold">Generate Tactical Guide</h3>
                                <p className="text-sm text-muted-foreground">
                                    Create a custom Sequoia-style guide for "{currentQuestion?.label || 'this topic'}"
                                </p>
                            </div>
                            <Button onClick={generateAiGuide} disabled={isGenerating}>
                                {isGenerating ? (
                                    <>
                                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                        Researching...
                                    </>
                                ) : (
                                    "Generate Guide"
                                )}
                            </Button>
                        </div>
                    ) : (
                        <div className="prose prose-sm dark:prose-invert max-w-none">
                            <div className="flex items-center justify-between mb-4 pb-4 border-b border-border/50">
                                <span className="text-xs font-medium text-primary bg-primary/10 px-2 py-1 rounded-full">
                                    AI Generated Resource
                                </span>
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={generateAiGuide}
                                    disabled={isGenerating}
                                    className="h-6 text-xs"
                                >
                                    Regenerate
                                </Button>
                            </div>
                            <ReactMarkdown>{aiArticle}</ReactMarkdown>

                            {/* Chat History Display */}
                            {chatHistory.length > 0 && (
                                <div className="mt-8 pt-8 border-t border-border space-y-4">
                                    <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-4">Discussion</h4>
                                    {chatHistory.map((msg, i) => (
                                        <div key={i} className={cn(
                                            "flex gap-3 text-sm",
                                            msg.role === "user" ? "justify-end" : "justify-start"
                                        )}>
                                            <div className={cn(
                                                "px-4 py-2 rounded-2xl max-w-[85%]",
                                                msg.role === "user"
                                                    ? "bg-primary text-primary-foreground rounded-tr-none"
                                                    : "bg-muted text-foreground rounded-tl-none"
                                            )}>
                                                {msg.content}
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
                                </div>
                            )}
                        </div>
                    )}
                </ScrollArea>

                {/* Chat Input (Only visible if article exists) */}
                {aiArticle && (
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
                                    className="w-full px-4 py-2 pr-10 rounded-full border border-border bg-muted/50 focus:outline-none focus:ring-1 focus:ring-primary text-sm"
                                    disabled={isChatting}
                                />
                            </div>
                            <Button
                                type="submit"
                                size="icon"
                                className="h-9 w-9 rounded-full"
                                disabled={!chatMessage.trim() || isChatting}
                            >
                                <Send className="w-4 h-4" />
                            </Button>
                        </form>
                    </div>
                )}
            </TabsContent>
        </Tabs>
      </div>
    </>
  )
}
