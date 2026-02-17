"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowRight, Phone, PhoneOff } from "lucide-react"
import { Button } from "@/components/ui/button"
import { StepIndicator } from "@/components/step-indicator"
import { ResourceSidebar } from "@/components/resource-sidebar"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { OFFLINE } from "@/lib/mode"
import { TextAgentChat } from "@/components/text-agent-chat"
import {
  LiveKitRoom,
  useVoiceAssistant,
  BarVisualizer,
  RoomAudioRenderer,
  DisconnectButton,
} from "@livekit/components-react"
import "@livekit/components-styles"

// Resources that appear during the call
const RESOURCES = [
  {
    id: "1",
    title: "Value Proposition Canvas",
    type: "framework" as const,
    description: "A tool to ensure your product fits customer needs and jobs-to-be-done.",
  },
  {
    id: "2", 
    title: "Customer Segmentation Guide",
    type: "article" as const,
    description: "How to identify and prioritize your ideal customer segments.",
  },
  {
    id: "3",
    title: "Competitive Moat Analysis",
    type: "framework" as const,
    description: "Framework for identifying sustainable competitive advantages.",
  },
]

const EXTRACTED_INSIGHTS = [
  { category: "problem" as const, title: "Core Problem", content: "Market gap identified in target space", source: "mentorship" as const },
  { category: "solution" as const, title: "Unique Value Prop", content: "Differentiated approach to solving the problem", source: "mentorship" as const },
  { category: "market" as const, title: "Target Market", content: "Initial customer segment defined", source: "mentorship" as const },
  { category: "competition" as const, title: "Competitive Landscape", content: "Key competitors and differentiation mapped", source: "mentorship" as const },
]

function VoiceUI({ onStateChange }: { onStateChange?: (speaking: boolean) => void }) {
  const { state, audioTrack } = useVoiceAssistant()

  useEffect(() => {
    onStateChange?.(state === "speaking")
  }, [state, onStateChange])

  return (
    <div className="flex flex-col items-center justify-center gap-6">
      {/* Same circle design as before connecting */}
      <div 
        className={cn(
          "w-64 h-64 md:w-80 md:h-80 rounded-full flex items-center justify-center relative",
          "bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20",
          "transition-all duration-300",
          state === "speaking" && "border-primary/40 from-primary/30"
        )}
      >
        {/* Pulse ring when speaking */}
        {state === "speaking" && (
          <div className="absolute inset-0 rounded-full border-2 border-primary/30 animate-ping" />
        )}
        
        <div className="flex flex-col items-center gap-2">
          <Phone className={cn(
            "w-12 h-12 transition-all duration-300",
            state === "speaking" ? "text-primary scale-110" : "text-primary/60"
          )} />
          <span className="text-muted-foreground text-sm">
            {state === "listening"
              ? "Listening..."
              : state === "thinking"
              ? "Thinking..."
              : state === "speaking"
              ? "Mentor speaking..."
              : "Connected"}
          </span>
        </div>
      </div>
      
      {/* Hidden audio visualizer for functionality */}
      <div className="sr-only">
        <BarVisualizer
          state={state}
          barCount={5}
          trackRef={audioTrack}
          options={{ minHeight: 10 }}
        />
      </div>
    </div>
  )
}

export default function MentorshipPage() {
  const router = useRouter()
  const { 
    idea, 
    setIdea,
    addInsight, 
    addResource, 
    unlockDashboard,
    setMentorshipCallCompleted,
    dashboardUnlocked 
  } = useAppStore()

  const [isVisible, setIsVisible] = useState(false)
  const [callActive, setCallActive] = useState(false)
  const [callEnded, setCallEnded] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [displayedResources, setDisplayedResources] = useState<Array<{
    id: string
    title: string
    type: "article" | "framework" | "example" | "metric"
    description: string
  }>>([])
  const [callDuration, setCallDuration] = useState(0)
  
  // LiveKit connection state
  const [token, setToken] = useState<string | null>(null)
  const [wsUrl, setWsUrl] = useState<string | null>(null)
  const [roomName] = useState(() => `mentorship-${Date.now()}`)

  // Load idea from sessionStorage on mount
  useEffect(() => {
    const storedIdea = sessionStorage.getItem("startup-idea")
    if (storedIdea && !idea) {
      setIdea(storedIdea)
    }
    setTimeout(() => setIsVisible(true), 50)
  }, [idea, setIdea])

  // Call duration timer
  useEffect(() => {
    if (!callActive || callEnded) return
    const interval = setInterval(() => {
      setCallDuration((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(interval)
  }, [callActive, callEnded])

  // Add resources progressively during the call
  useEffect(() => {
    if (!callActive || callEnded) return

    const timeouts: NodeJS.Timeout[] = []
    
    RESOURCES.forEach((resource, index) => {
      const timeout = setTimeout(() => {
        setDisplayedResources((prev) => [...prev, resource])
        addResource(resource)
      }, (index + 1) * 15000) // Add a resource every 15 seconds
      timeouts.push(timeout)
    })

    return () => timeouts.forEach(clearTimeout)
  }, [callActive, callEnded, addResource])

  const fetchToken = useCallback(async () => {
    try {
      // Include the startup idea in the token request
      const params = new URLSearchParams({
        room: roomName,
        ...(idea && { idea }),
      })
      const response = await fetch(`/api/token?${params.toString()}`)
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.error || "Failed to get token")
      }
      
      setToken(data.token)
      setWsUrl(data.url)
    } catch (err) {
      console.error("Failed to fetch token:", err)
    }
  }, [roomName, idea])

  const startCall = useCallback(async () => {
    if (!OFFLINE) await fetchToken()
    setCallActive(true)
    setCallDuration(0)
  }, [fetchToken])

  const endCall = useCallback(() => {
    setCallActive(false)
    setCallEnded(true)
    setIsSpeaking(false)
    setToken(null)

    // Persist insights to global state
    EXTRACTED_INSIGHTS.forEach((insight) => {
      addInsight(insight)
    })

    unlockDashboard()
    setMentorshipCallCompleted(true)
  }, [addInsight, unlockDashboard, setMentorshipCallCompleted])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const steps = [
    { id: "mentorship", label: "Mentorship Call", current: true, completed: callEnded },
    { id: "dashboard", label: "Product Dashboard", current: false, completed: false },
  ]

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
          {/* Logo - links to dashboard only if unlocked */}
          <Link 
            href={dashboardUnlocked ? "/dashboard" : "#"} 
            className={cn(
              "font-serif text-xl font-semibold transition-colors",
              dashboardUnlocked ? "text-foreground hover:text-primary" : "text-muted-foreground cursor-default"
            )}
          >
            Launchpad
          </Link>

          {/* Step Indicator */}
          <StepIndicator steps={steps} />

          {/* Call status */}
          <div className="flex items-center gap-3">
            {callActive && !callEnded && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10">
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                <span className="text-sm font-medium text-primary">
                  {formatDuration(callDuration)}
                </span>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div 
        className={cn(
          "flex-1 flex pt-16 transition-all duration-500",
          isVisible ? "opacity-100" : "opacity-0"
        )}
      >
        {/* Center Content */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 relative">
          {/* Idea context card */}
          {idea && !(OFFLINE && callActive) && (
            <div 
              className={cn(
                "absolute top-24 left-1/2 -translate-x-1/2 max-w-md w-full",
                "bg-card/80 backdrop-blur-sm border border-border rounded-2xl p-4",
                "transition-all duration-500",
                callActive ? "opacity-50 scale-95" : "opacity-100 scale-100"
              )}
            >
              <p className="text-xs text-muted-foreground font-medium mb-1">Your idea</p>
              <p className="text-sm text-foreground line-clamp-2">{idea}</p>
            </div>
          )}

          {/* Voice Interface */}
          <div className="flex-1 flex items-center justify-center w-full">
            {OFFLINE && callActive && !callEnded ? (
              <TextAgentChat
                mode="mentor"
                idea={idea || undefined}
                className="w-full max-w-2xl h-[min(600px,calc(100vh-14rem))]"
              />
            ) : callActive && !callEnded && token && wsUrl ? (
              <LiveKitRoom
                token={token}
                serverUrl={wsUrl}
                connect={true}
                audio={true}
                video={false}
                onDisconnected={endCall}
                className="flex-1 flex flex-col items-center justify-center h-full w-full"
              >
                <VoiceUI onStateChange={setIsSpeaking} />
                <RoomAudioRenderer />
              </LiveKitRoom>
            ) : callActive && !callEnded && !token ? (
              // Connecting state - show icon while fetching token
              <div 
                className={cn(
                  "w-64 h-64 md:w-80 md:h-80 rounded-full flex items-center justify-center",
                  "bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20",
                  "transition-all duration-300 animate-pulse"
                )}
              >
                <div className="flex flex-col items-center gap-2">
                  <Phone className="w-12 h-12 text-primary/60" />
                  <span className="text-muted-foreground text-sm">
                    Connecting...
                  </span>
                </div>
              </div>
            ) : (
              <div 
                className={cn(
                  "w-64 h-64 md:w-80 md:h-80 rounded-full flex items-center justify-center",
                  "bg-gradient-to-br from-primary/20 to-primary/5 border border-primary/20",
                  "transition-all duration-300"
                )}
              >
                <div className="flex flex-col items-center gap-2">
                  <Phone className="w-12 h-12 text-primary/60" />
                  <span className="text-muted-foreground text-sm">
                    {callEnded ? "Call ended" : OFFLINE ? "Ready to chat" : "Ready to connect"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Call Controls */}
          {!callEnded && (
            <div className="flex items-center gap-4 mb-8">
              {!callActive ? (
                <Button
                  onClick={startCall}
                  size="lg"
                  className="gap-2 rounded-full px-8"
                >
                  <Phone className="w-4 h-4" />
                  {OFFLINE ? "Start Mentor Chat" : "Start Mentorship Call"}
                </Button>
              ) : (
                <Button
                  onClick={endCall}
                  variant="destructive"
                  size="lg"
                  className="gap-2 rounded-full px-8"
                >
                  <PhoneOff className="w-4 h-4" />
                  {OFFLINE ? "End Chat" : "End Call"}
                </Button>
              )}
            </div>
          )}
        </div>

        {/* Resource Sidebar */}
        <ResourceSidebar 
          resources={displayedResources} 
          className="hidden lg:flex h-[calc(100vh-4rem)] fixed right-0 top-16" 
        />
      </div>

      {/* End of Call Banner */}
      {callEnded && (
        <div 
          className={cn(
            "fixed bottom-0 left-0 right-0 z-50",
            "bg-gradient-to-t from-primary/10 via-background to-transparent",
            "border-t border-primary/20",
            "animate-in slide-in-from-bottom duration-500"
          )}
        >
          <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-foreground">Insights captured</p>
                <p className="text-sm text-muted-foreground">
                  {EXTRACTED_INSIGHTS.length} key insights extracted from your mentorship call
                </p>
              </div>
            </div>
            
            <Button
              onClick={() => router.push("/dashboard")}
              size="lg"
              className="gap-2 rounded-full px-6 group"
            >
              Build your dashboard
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Button>
          </div>
        </div>
      )}
    </main>
  )
}
