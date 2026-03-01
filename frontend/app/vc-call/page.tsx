"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { ArrowRight, Phone, PhoneOff, DollarSign } from "lucide-react"
import { Button } from "@/components/ui/button"
import { StepIndicator } from "@/components/step-indicator"
import { useAppStore, type VCReport } from "@/lib/store"
import { cn } from "@/lib/utils"
import {
  LiveKitRoom,
  useVoiceAssistant,
  BarVisualizer,
  RoomAudioRenderer,
  useRoomContext,
} from "@livekit/components-react"
import "@livekit/components-styles"
import { Loader2 } from "lucide-react"
import { OFFLINE } from "@/lib/mode"
import { TextAgentChat } from "@/components/text-agent-chat"

function VoiceUI({ onStateChange }: { onStateChange?: (speaking: boolean) => void }) {
  const { state, audioTrack } = useVoiceAssistant()

  useEffect(() => {
    onStateChange?.(state === "speaking")
  }, [state, onStateChange])

  return (
    <div className="flex flex-col items-center justify-center gap-6">
      {/* VC-themed circle design */}
      <div 
        className={cn(
          "w-64 h-64 md:w-80 md:h-80 rounded-full flex items-center justify-center relative",
          "bg-gradient-to-br from-indigo-500/20 to-purple-500/5 border border-indigo-500/20",
          "transition-all duration-300",
          state === "speaking" && "border-indigo-500/40 from-indigo-500/30"
        )}
      >
        {/* Pulse ring when speaking */}
        {state === "speaking" && (
          <div className="absolute inset-0 rounded-full border-2 border-indigo-500/30 animate-ping" />
        )}
        
        <div className="flex flex-col items-center gap-2">
          {state === "speaking" ? (
             <DollarSign className="w-12 h-12 text-indigo-500 scale-110 transition-all duration-300" />
          ) : (
             <Phone className="w-12 h-12 text-indigo-500/60 transition-all duration-300" />
          )}
          <span className="text-muted-foreground text-sm font-medium">
            {state === "listening"
              ? "VC is listening..."
              : state === "thinking"
              ? "Evaluating..."
              : state === "speaking"
              ? "Partner speaking..."
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

function CallControls({ onLeave }: { onLeave: () => void }) {
  const room = useRoomContext()
  const router = useRouter()
  const { setVcReport } = useAppStore()
  const [isGenerating, setIsGenerating] = useState(false)

  const handleEndCall = async () => {
    setIsGenerating(true)
    
    try {
      if (room.localParticipant) {
        // Fire and forget - tell agent to generate
        const payload = new TextEncoder().encode(JSON.stringify({ type: "generate_report" }))
        await room.localParticipant.publishData(payload, { reliable: true })
      }
    } catch (e) {
      console.error("Error asking for report:", e)
    } finally {
        // Disconnect immediately 
         setIsGenerating(false)
         room.disconnect()
         onLeave()
         router.push("/dashboard")
    }
  }

  return (
    <div className="flex items-center gap-4 mb-8">
      <Button
        onClick={handleEndCall}
        variant="destructive"
        size="lg"
        disabled={isGenerating}
        className="gap-2 rounded-full px-8"
      >
        <PhoneOff className="w-4 h-4" />
        End Pitch
      </Button>
    </div>
  )
}

export default function VcCallPage() {
  const router = useRouter()
  const { 
    idea, 
    setIdea,
    setVcCallCompleted,
    setVcReport,
    autoFillModules,
    dashboardUnlocked 
  } = useAppStore()
  const [reportRequested, setReportRequested] = useState(false)

  const [isVisible, setIsVisible] = useState(false)
  const [callActive, setCallActive] = useState(false)
  const [callEnded, setCallEnded] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [callDuration, setCallDuration] = useState(0)
  
  // LiveKit connection state
  const [token, setToken] = useState<string | null>(null)
  const [wsUrl, setWsUrl] = useState<string | null>(null)
  const [roomName] = useState(() => `vc-pitch-${Date.now()}`)

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

  const fetchToken = useCallback(async () => {
    try {
      // Include the startup idea and mode='vc' in the token request
      const params = new URLSearchParams({
        room: roomName,
        mode: "vc",
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
    setVcCallCompleted(true)
  }, [setVcCallCompleted])

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, "0")}`
  }

  const steps = [
    { id: "dashboard", label: "Dashboard", current: false, completed: true },
    { id: "vc-call", label: "VC Pitch", current: true, completed: callEnded },
  ]

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <Link 
            href={dashboardUnlocked ? "/dashboard" : "#"} 
            className="font-serif text-xl font-semibold text-foreground hover:text-primary transition-colors"
          >
            Launchpad
          </Link>

          {/* Step Indicator */}
          <div className="hidden sm:block">
            <StepIndicator steps={steps} />
          </div>

          {/* Call status */}
          <div className="flex items-center gap-3">
            {callActive && !callEnded && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-500/10">
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-sm font-medium text-red-500">
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
        <div className="flex-1 min-w-0 flex flex-col items-center justify-center p-4 sm:p-6 relative">
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
              <div className="flex items-center gap-2 mb-1">
                 <DollarSign className="w-3 h-3 text-indigo-500" />
                 <p className="text-xs text-muted-foreground font-medium">Your Pitch</p>
              </div>
              <p className="text-sm text-foreground line-clamp-2">{idea}</p>
            </div>
          )}

          {/* Voice Interface */}
          <div className="flex-1 flex flex-col items-center justify-center w-full gap-4">
            {OFFLINE && callActive && !callEnded ? (
              <>
                <TextAgentChat
                  mode="vc"
                  idea={idea || undefined}
                  reportRequested={reportRequested}
                  onReport={(report) => {
                    if (report) {
                      const vcReport = report as unknown as VCReport
                      setVcReport(vcReport)
                      if (vcReport.extraction) autoFillModules(vcReport.extraction)
                    }
                    endCall()
                    router.push("/dashboard")
                  }}
                  className="w-full max-w-2xl h-[min(560px,calc(100vh-16rem))]"
                />
                <Button
                  onClick={() => setReportRequested(true)}
                  variant="destructive"
                  size="lg"
                  disabled={reportRequested}
                  className="gap-2 rounded-full px-8"
                >
                  {reportRequested ? <Loader2 className="w-4 h-4 animate-spin" /> : <PhoneOff className="w-4 h-4" />}
                  End Pitch
                </Button>
              </>
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
                
                {/* Controls - Inside Room Context */}
                <div className="absolute bottom-0 left-0 right-0 flex justify-center">
                    <CallControls onLeave={() => {
                        endCall()
                    }} />
                </div>
              </LiveKitRoom>
            ) : callActive && !callEnded && !token ? (
              // Connecting state - show icon while fetching token
              <div 
                className={cn(
                  "w-64 h-64 md:w-80 md:h-80 rounded-full flex items-center justify-center",
                  "bg-gradient-to-br from-indigo-500/20 to-purple-500/5 border border-indigo-500/20",
                  "transition-all duration-300 animate-pulse"
                )}
              >
                <div className="flex flex-col items-center gap-2">
                  <Phone className="w-12 h-12 text-indigo-500/60" />
                  <span className="text-muted-foreground text-sm">
                    Connecting to Partner...
                  </span>
                </div>
              </div>
            ) : (
              <div 
                className={cn(
                  "w-64 h-64 md:w-80 md:h-80 rounded-full flex items-center justify-center",
                  "bg-gradient-to-br from-indigo-500/20 to-purple-500/5 border border-indigo-500/20",
                  "transition-all duration-300"
                )}
              >
                <div className="flex flex-col items-center gap-2">
                  <DollarSign className="w-12 h-12 text-indigo-500/60" />
                  <span className="text-muted-foreground text-sm">
                    {callEnded ? "Pitch Completed" : "Ready to Pitch"}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Call Controls */}
          {!callEnded && !callActive && (
            <div className="flex items-center gap-4 mb-8">
                <Button
                  onClick={startCall}
                  size="lg"
                  className="gap-2 rounded-full px-8 bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  <Phone className="w-4 h-4" />
                  {OFFLINE ? "Start Text Pitch" : "Start VC Pitch"}
                </Button>
            </div>
          )}
        </div>
      </div>

      {/* End of Call Banner */}
      {callEnded && (
        <div 
          className={cn(
            "fixed bottom-0 left-0 right-0 z-50",
            "bg-gradient-to-t from-background via-background to-transparent",
            "border-t border-border",
            "animate-in slide-in-from-bottom duration-500"
          )}
        >
          <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-indigo-500" />
              </div>
              <div>
                <p className="font-medium text-foreground">Pitch Completed</p>
                <p className="text-sm text-muted-foreground">
                   Great job! Return to the dashboard to refine your strategy.
                </p>
              </div>
            </div>
            
            <Button
              onClick={() => router.push("/dashboard")}
              size="lg"
              className="gap-2 rounded-full px-6 group"
            >
              Back to Dashboard
              <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
            </Button>
          </div>
        </div>
      )}
    </main>
  )
}
