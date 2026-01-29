"use client"

import React from "react"

import { useState } from "react"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { ArrowRight, Sparkles } from "lucide-react"

interface IdeaInputBubbleProps {
  value: string
  onChange: (value: string) => void
  onSubmit: () => void
  disabled?: boolean
}

export function IdeaInputBubble({ value, onChange, onSubmit, disabled }: IdeaInputBubbleProps) {
  const [isFocused, setIsFocused] = useState(false)

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && e.metaKey) {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div 
      className={`
        relative mx-4 md:mx-0
        transition-all duration-300 ease-out
        ${isFocused ? "scale-[1.02]" : "scale-100"}
      `}
      style={{ width: 'min(33vw, 500px)', minWidth: '320px' }}
    >
      {/* Glow effect on focus */}
      <div 
        className={`
          absolute -inset-1 rounded-3xl bg-primary/20 blur-xl
          transition-opacity duration-300
          ${isFocused ? "opacity-100" : "opacity-0"}
        `}
      />
      
      {/* Main bubble container */}
      <div 
        className={`
          relative bg-card border-2 rounded-3xl p-6 md:p-8
          shadow-lg shadow-primary/5
          transition-all duration-300
          ${isFocused ? "border-primary/40" : "border-border"}
        `}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-primary" />
          <span className="text-sm font-medium text-muted-foreground">
            What&apos;s your startup idea?
          </span>
        </div>

        {/* Textarea */}
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your idea in a few sentences. What problem does it solve? Who is it for?"
          className="
            w-full h-[140px] min-h-[140px] max-h-[140px] resize-none border-0 p-0
            text-base md:text-lg leading-relaxed
            bg-transparent placeholder:text-muted-foreground/50
            focus-visible:ring-0 focus-visible:ring-offset-0
            overflow-y-auto
          "
          style={{ width: '100%' }}
          disabled={disabled}
        />

        {/* Footer with CTA */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t border-border/50">
          <span className="text-xs text-muted-foreground hidden sm:block">
            Press <kbd className="px-1.5 py-0.5 text-xs bg-secondary rounded font-mono">Cmd</kbd> + <kbd className="px-1.5 py-0.5 text-xs bg-secondary rounded font-mono">Enter</kbd> to continue
          </span>
          
          <Button
            onClick={onSubmit}
            disabled={!value.trim() || disabled}
            className="
              ml-auto group
              bg-primary hover:bg-primary/90 text-primary-foreground
              px-6 py-5 rounded-xl font-semibold
              transition-all duration-200
              disabled:opacity-40 disabled:cursor-not-allowed
            "
          >
            Start Mentorship
            <ArrowRight className="ml-2 w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Button>
        </div>
      </div>
    </div>
  )
}
