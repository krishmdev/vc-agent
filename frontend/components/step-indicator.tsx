"use client"

import { cn } from "@/lib/utils"
import { Check, ChevronRight } from "lucide-react"

interface Step {
  id: string
  label: string
  completed?: boolean
  current?: boolean
}

interface StepIndicatorProps {
  steps: Step[]
  className?: string
}

export function StepIndicator({ steps, className }: StepIndicatorProps) {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      {steps.map((step, index) => (
        <div key={step.id} className="flex items-center">
          <div
            className={cn(
              "flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-300",
              step.current && "bg-primary/10 text-primary",
              step.completed && !step.current && "text-primary/70",
              !step.current && !step.completed && "text-muted-foreground/60"
            )}
          >
            {step.completed && !step.current && (
              <Check className="w-3.5 h-3.5" />
            )}
            <span>{step.label}</span>
          </div>
          
          {index < steps.length - 1 && (
            <ChevronRight 
              className={cn(
                "w-4 h-4 mx-1 transition-colors duration-300",
                step.completed ? "text-primary/50" : "text-muted-foreground/30"
              )} 
            />
          )}
        </div>
      ))}
    </div>
  )
}
