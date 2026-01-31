"use client"

import { useState, useEffect, useRef } from "react"
import { Send, Bot, User, Loader2, Sparkles, X, Minimize2, Maximize2 } from "lucide-react"
import ReactMarkdown from "react-markdown"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface Message {
  role: "user" | "assistant"
  content: string
  id: string
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

export function ResearchChat({ isOpen, onClose, initialContext }: ResearchChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isLoading])

  // Polling for active task
  useEffect(() => {
    let pollInterval: NodeJS.Timeout;

    if (currentTaskId) {
        pollInterval = setInterval(async () => {
            try {
                // Poll the Next.js API route which proxies to the backend
                // logic: GET /api/research?taskId=...&action=status
                const res = await fetch(`/api/research?taskId=${currentTaskId}&action=status`); 
                
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === "completed") {
                        // Add assistant message
                        setMessages(prev => [
                            ...prev, 
                            { 
                                role: "assistant", 
                                content: data.content, 
                                id: Date.now().toString() 
                            }
                        ]);
                        setIsLoading(false);
                        setCurrentTaskId(null);
                        clearInterval(pollInterval);
                    } else if (data.status === "failed") {
                        setMessages(prev => [
                            ...prev, 
                            { 
                                role: "assistant", 
                                content: `Error: ${data.error || "Research failed."}`, 
                                id: Date.now().toString() 
                            }
                        ]);
                        setIsLoading(false);
                        setCurrentTaskId(null);
                        clearInterval(pollInterval);
                    }
                }
            } catch (e) {
                console.error("Polling error", e);
            }
        }, 3000);
    }

    return () => clearInterval(pollInterval);
  }, [currentTaskId]);

  // Initial trigger if context provided and no messages
  useEffect(() => {
     if (isOpen && messages.length === 0 && !isLoading && initialContext?.idea) {
         handleSendMessage("Start research based on provided context.", true);
     }
  }, [isOpen, messages.length, initialContext]);

  const handleSendMessage = async (text: string, isSystemTrigger = false) => {
    if (!text.trim() && !isSystemTrigger) return;

    const userMsg: Message = { role: "user", content: text, id: Date.now().toString() };
    if (!isSystemTrigger) {
        setMessages(prev => [...prev, userMsg]);
    }
    
    setInput("");
    setIsLoading(true);

    try {
        const body = {
            message: text,
            session_id: sessionId,
            ...initialContext
        };

        const res = await fetch("/api/research", {
            method: "POST",
            body: JSON.stringify(body),
            headers: { "Content-Type": "application/json" }
        });

        if (!res.ok) throw new Error("Failed to send message");
        
        const data = await res.json();
        setSessionId(data.session_id);
        setCurrentTaskId(data.task_id);
    } catch (e) {
        console.error(e);
        setIsLoading(false);
        setMessages(prev => [...prev, { role: "assistant", content: "Failed to connect to research agent.", id: Date.now().toString() }]);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full md:w-[600px] lg:w-[800px] bg-background border-l border-border shadow-2xl z-50 flex flex-col transition-transform duration-300 ease-in-out">
      {/* Header */}
      <div className="h-14 border-b border-border flex items-center justify-between px-4 bg-secondary/30 backdrop-blur-sm">
        <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-primary" />
            </div>
            <div>
                <h3 className="font-semibold text-sm">Problem Space Specialist</h3>
                <p className="text-xs text-muted-foreground">Deep Research Agent</p>
            </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
        </Button>
      </div>

      {/* Chat Area */}
      <div className="flex-1 p-4 bg-muted/10 overflow-y-auto min-h-0 scroll-smooth">
        <div className="space-y-6 max-w-3xl mx-auto">
            {messages.length === 0 && !isLoading && (
                <div className="text-center text-muted-foreground mt-20">
                    <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Ready to research your problem space.</p>
                    <p className="text-sm">Ask me to analyze a market, competitors, or validate a problem.</p>
                </div>
            )}

            {messages.map((msg) => (
                <div key={msg.id} className={cn("flex gap-3", msg.role === "user" ? "flex-row-reverse" : "flex-row")}>
                    <div className={cn(
                        "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                        msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
                    )}>
                        {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>
                    <div className={cn(
                        "rounded-lg p-4 max-w-[85%] text-sm",
                        msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-card border border-border prose prose-sm dark:prose-invert max-w-none"
                    )}>
                        {msg.role === "assistant" ? (
                            <ReactMarkdown
                                components={{
                                    h1: ({node, ...props}) => <h1 className="text-2xl font-bold mt-8 mb-4 pb-2 border-b border-border" {...props} />,
                                    h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-6 mb-3 text-primary" {...props} />,
                                    h3: ({node, ...props}) => <h3 className="text-lg font-semibold mt-4 mb-2" {...props} />,
                                    p: ({node, ...props}) => <p className="mb-4 leading-relaxed" {...props} />,
                                    ul: ({node, ...props}) => <ul className="list-disc pl-6 mb-4 space-y-1" {...props} />,
                                    ol: ({node, ...props}) => <ol className="list-decimal pl-6 mb-4 space-y-1" {...props} />,
                                    li: ({node, ...props}) => <li className="mb-1" {...props} />,
                                    a: ({node, ...props}) => <a className="text-primary hover:underline font-medium" target="_blank" rel="noopener noreferrer" {...props} />,
                                    strong: ({node, ...props}) => <strong className="font-semibold text-foreground" {...props} />,
                                }}
                            >
                                {msg.content}
                            </ReactMarkdown>
                        ) : (
                            msg.content
                        )}
                    </div>
                </div>
            ))}

            {isLoading && (
                <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center shrink-0">
                        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                    </div>
                    <div className="bg-card border border-border rounded-lg p-4 text-sm text-muted-foreground animate-pulse">
                        {messages.length > 0 ? "Searching for helpful resources..." : "Conducting deep research... this may take 2-5 minutes."}
                    </div>
                </div>
            )}
            <div ref={scrollRef} className="h-4" />
        </div>
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-border bg-background">
        <form 
            onSubmit={(e) => { e.preventDefault(); handleSendMessage(input); }}
            className="flex gap-2 max-w-3xl mx-auto"
        >
            <Input 
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a follow-up or refine the scope..."
                disabled={isLoading}
                className="flex-1"
            />
            <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
                <Send className="w-4 h-4" />
            </Button>
        </form>
      </div>
    </div>
  )
}
