"use client"

import { useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { IdeaInputBubble } from "@/components/idea-input-bubble"
import { useAppStore } from "@/lib/store"

export default function LandingPage() {
  const { setIdea } = useAppStore()
  const [localIdea, setLocalIdea] = useState("")
  const [isTransitioning, setIsTransitioning] = useState(false)
  const bubbleRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const idea = ""; // Declare the idea variable

  const handleStartMentorship = () => {
    if (!localIdea.trim()) return
    
    setIsTransitioning(true)
    
    // Persist idea to global store and sessionStorage
    setIdea(localIdea)
    sessionStorage.setItem("startup-idea", localIdea)
    
    // Wait for animation to complete before navigating
    setTimeout(() => {
      router.push("/mentorship")
    }, 600)
  }

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center relative overflow-hidden">
      {/* Subtle background pattern */}
      <div className="absolute inset-0 opacity-[0.03]">
        <svg className="w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="60" height="60" patternUnits="userSpaceOnUse">
              <path d="M 60 0 L 0 0 0 60" fill="none" stroke="currentColor" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" className="text-foreground"/>
        </svg>
      </div>

      {/* Main content container */}
      <div 
        ref={bubbleRef}
        className={`relative z-10 flex flex-col items-center transition-all duration-500 ease-out ${
          isTransitioning 
            ? "scale-75 opacity-0 translate-y-[-100px]" 
            : "scale-100 opacity-100 translate-y-0"
        }`}
      >
        {/* Brand wordmark */}
        <div className="mb-12">
          <h1 className="font-serif text-3xl md:text-4xl font-semibold text-foreground tracking-tight">
            Launchpad
          </h1>
        </div>

        {/* Idea Input Bubble */}
        <IdeaInputBubble
          value={localIdea}
          onChange={setLocalIdea}
          onSubmit={handleStartMentorship}
          disabled={isTransitioning}
        />

        {/* Progress indicator */}
        <div className="mt-8 flex flex-col items-center gap-3">
          <div className="flex items-center gap-2">
            {[1, 2, 3, 4].map((step) => (
              <div
                key={step}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  step === 1 
                    ? "w-6 bg-primary" 
                    : "w-1.5 bg-border"
                }`}
              />
            ))}
          </div>
          <p className="text-sm text-muted-foreground font-medium">
            Step 1 of 4: Clarify your idea
          </p>
        </div>
      </div>

      {/* Decorative elements */}
      <div className="absolute bottom-8 left-8 text-muted-foreground/40 font-mono text-xs hidden md:block">
        From idea to validation
      </div>
      
      <div className="absolute bottom-8 right-8 text-muted-foreground/40 font-mono text-xs hidden md:block">
        Powered by AI mentorship
      </div>
    </main>
  )
}
