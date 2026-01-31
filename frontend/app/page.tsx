"use client"

import { useState, useRef } from "react"
import { useRouter } from "next/navigation"
import { IdeaInputBubble } from "@/components/idea-input-bubble"
import { useAppStore } from "@/lib/store"

export default function LandingPage() {
  const { setIdea, unlockDashboard } = useAppStore()
  const [localIdea, setLocalIdea] = useState("")
  const [isTransitioning, setIsTransitioning] = useState(false)
  const bubbleRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const idea = ""; // Declare the idea variable

  const handleStartMentorship = async () => {
    if (!localIdea.trim()) return // Use localIdea for validation
    
    setIsTransitioning(true)
    
    // Persist idea to global store and sessionStorage
    setIdea(localIdea)
    sessionStorage.setItem("startup-idea", localIdea)
    
    // Unlock the dashboard
    unlockDashboard()

    // Redirect to mentor call
    router.push("/mentorship")
  }

  return (
    <main className="min-h-screen bg-background flex flex-col items-center justify-center relative overflow-hidden">
      {/* Sequoia tree illustrations */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Left Side Group - Scaled up 30% */}
        <svg 
          className="absolute left-0 bottom-0 w-80 h-[42rem] opacity-70" 
          viewBox="0 0 200 400" 
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="xMidYMax meet"
        >
          {/* Tree 1: Sage Green, Tall */}
          <g transform="translate(20, 100)">
             <rect x="35" y="220" width="10" height="80" fill="#8C867D" />
             {/* Stacked Triangles */}
             <path d="M 40 40 L 10 120 L 70 120 Z" fill="#8FA89B" />
             <path d="M 40 90 L 5 180 L 75 180 Z" fill="#8FA89B" />
             <path d="M 40 150 L 0 240 L 80 240 Z" fill="#8FA89B" />
          </g>
          
          {/* Tree 2: Muted Earth, Medium */}
          <g transform="translate(80, 150)">
             <rect x="35" y="180" width="10" height="70" fill="#9D9488" />
             <path d="M 40 60 L 15 130 L 65 130 Z" fill="#B2C2B8" />
             <path d="M 40 100 L 10 190 L 70 190 Z" fill="#B2C2B8" />
          </g>

          {/* Tree 3: Pale Green (Fixed from brown), Small */}
          <g transform="translate(130, 200)">
             <rect x="30" y="140" width="8" height="60" fill="#8C867D" />
             <path d="M 34 80 L 14 150 L 54 150 Z" fill="#9CAFAA" />
          </g>
        </svg>

        {/* Right Side Group - Scaled up 30% */}
        <svg 
          className="absolute right-0 bottom-0 w-96 h-[47rem] opacity-70" 
          viewBox="0 0 200 400" 
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="xMidYMax meet"
        >
          {/* Tree 1: Tall Sage */}
          <g transform="translate(100, 80)">
             <rect x="35" y="240" width="12" height="80" fill="#8C867D" />
             <path d="M 41 20 L 15 100 L 67 100 Z" fill="#94AFA0" />
             <path d="M 41 70 L 5 170 L 77 170 Z" fill="#94AFA0" />
             <path d="M 41 140 L -5 250 L 87 250 Z" fill="#94AFA0" />
          </g>

           {/* Tree 2: Muted Green */}
           <g transform="translate(20, 160)">
             <rect x="35" y="180" width="10" height="60" fill="#9D9488" />
             <path d="M 40 80 L 15 160 L 65 160 Z" fill="#B0BDB5" />
             <path d="M 40 130 L 5 210 L 75 210 Z" fill="#B0BDB5" />
          </g>
        </svg>
      </div>

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
    </main>
  )
}
