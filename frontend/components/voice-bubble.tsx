"use client"

import { useEffect, useState } from "react"
import { Mic, MicOff, Volume2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface VoiceBubbleProps {
  isActive: boolean
  isSpeaking: boolean
  onToggleMic?: () => void
  className?: string
}

export function VoiceBubble({ isActive, isSpeaking, onToggleMic, className }: VoiceBubbleProps) {
  const [pulsePhase, setPulsePhase] = useState(0)

  useEffect(() => {
    if (!isActive) return

    const interval = setInterval(() => {
      setPulsePhase((prev) => (prev + 1) % 360)
    }, 50)

    return () => clearInterval(interval)
  }, [isActive])

  // Calculate dynamic scale based on speaking state
  const baseScale = 1
  const speakingScale = isSpeaking ? 1 + Math.sin(pulsePhase * 0.1) * 0.08 : baseScale

  return (
    <div className={cn("relative flex items-center justify-center", className)}>
      {/* Outer glow rings */}
      <div
        className={cn(
          "absolute inset-0 rounded-full transition-all duration-1000",
          isActive ? "opacity-100" : "opacity-0"
        )}
        style={{
          background: `radial-gradient(circle, 
            oklch(0.42 0.1 145 / 0.15) 0%, 
            oklch(0.42 0.1 145 / 0.05) 50%, 
            transparent 70%
          )`,
          transform: `scale(${1.5 + Math.sin(pulsePhase * 0.02) * 0.1})`,
        }}
      />

      {/* Secondary pulse ring */}
      <div
        className={cn(
          "absolute inset-0 rounded-full transition-all duration-700",
          isSpeaking ? "opacity-60" : "opacity-20"
        )}
        style={{
          background: `radial-gradient(circle, 
            oklch(0.50 0.12 145 / 0.2) 0%, 
            oklch(0.50 0.12 145 / 0.08) 40%, 
            transparent 60%
          )`,
          transform: `scale(${1.3 + Math.sin((pulsePhase + 180) * 0.03) * 0.08})`,
        }}
      />

      {/* Main voice bubble */}
      <div
        className={cn(
          "relative w-48 h-48 md:w-64 md:h-64 rounded-full flex items-center justify-center",
          "transition-all duration-300 cursor-pointer"
        )}
        style={{
          background: `linear-gradient(
            ${135 + Math.sin(pulsePhase * 0.01) * 15}deg,
            oklch(0.35 0.08 145) 0%,
            oklch(0.42 0.1 145) 35%,
            oklch(0.50 0.12 145) 65%,
            oklch(0.45 0.1 145) 100%
          )`,
          boxShadow: `
            0 0 60px oklch(0.42 0.1 145 / 0.3),
            0 0 100px oklch(0.42 0.1 145 / 0.15),
            inset 0 0 60px oklch(0.55 0.12 145 / 0.2)
          `,
          transform: `scale(${speakingScale})`,
        }}
        onClick={onToggleMic}
      >
        {/* Inner highlight */}
        <div
          className="absolute inset-4 rounded-full opacity-30"
          style={{
            background: `radial-gradient(circle at 30% 30%, 
              oklch(0.70 0.08 145 / 0.4) 0%, 
              transparent 50%
            )`,
          }}
        />

        {/* Icon container */}
        <div className="relative z-10 flex flex-col items-center gap-3">
          {isSpeaking ? (
            <Volume2 className="w-12 h-12 md:w-16 md:h-16 text-primary-foreground animate-pulse" />
          ) : isActive ? (
            <Mic className="w-12 h-12 md:w-16 md:h-16 text-primary-foreground" />
          ) : (
            <MicOff className="w-12 h-12 md:w-16 md:h-16 text-primary-foreground/70" />
          )}
          
          <span className="text-primary-foreground/90 text-sm font-medium">
            {isSpeaking ? "Mentor speaking..." : isActive ? "Listening..." : "Click to start"}
          </span>
        </div>

        {/* Animated border particles */}
        {isActive && (
          <>
            {[...Array(6)].map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full bg-primary-foreground/40"
                style={{
                  top: "50%",
                  left: "50%",
                  transform: `
                    rotate(${(pulsePhase + i * 60) % 360}deg) 
                    translateY(-${96 + (i % 2) * 8}px)
                  `,
                  opacity: 0.4 + Math.sin((pulsePhase + i * 60) * 0.05) * 0.3,
                }}
              />
            ))}
          </>
        )}
      </div>
    </div>
  )
}
