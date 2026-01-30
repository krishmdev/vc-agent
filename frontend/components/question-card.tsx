"use client"

import { Question, ModuleId } from "@/lib/dashboard-types"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { CheckCircle2, Circle, HelpCircle } from "lucide-react"
import { useState, useEffect } from "react"

interface QuestionCardProps {
  question: Question
  moduleId: ModuleId
  onFocus?: () => void
}

export function QuestionCard({ question, moduleId, onFocus }: QuestionCardProps) {
  const updateQuestion = useAppStore((state) => state.updateQuestion)
  const [localValue, setLocalValue] = useState(question.value)

  // Sync local value with store when question changes
  useEffect(() => {
    setLocalValue(question.value)
  }, [question.value])

  const handleBlur = () => {
    // Only update if value has changed
    if (localValue !== question.value) {
      updateQuestion(moduleId, question.id, localValue)
    }
  }

  const handleChange = (value: string | string[]) => {
    setLocalValue(value)
  }

  const renderInput = () => {
    switch (question.type) {
      case 'text':
        return (
          <input
            type="text"
            value={localValue as string}
            onChange={(e) => handleChange(e.target.value)}
            onBlur={handleBlur}
            onFocus={onFocus}
            placeholder={question.placeholder}
            disabled={question.type === 'readonly'}
            className={cn(
              "w-full px-4 py-3 rounded-lg border border-border bg-background",
              "text-sm text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary",
              "transition-all duration-200",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          />
        )

      case 'textarea':
      case 'structured':
        return (
          <textarea
            value={localValue as string}
            onChange={(e) => handleChange(e.target.value)}
            onBlur={handleBlur}
            onFocus={onFocus}
            placeholder={question.placeholder}
            disabled={question.type === 'readonly'}
            rows={question.type === 'structured' ? 3 : 6}
            className={cn(
              "w-full px-4 py-3 rounded-lg border border-border bg-background",
              "text-sm text-foreground placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary",
              "transition-all duration-200 resize-none",
              "disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          />
        )

      case 'readonly':
        return (
          <div
            className={cn(
              "w-full px-4 py-3 rounded-lg border border-border/50 bg-muted/30",
              "text-sm text-muted-foreground italic min-h-[100px]"
            )}
          >
            {(localValue as string) || question.placeholder}
          </div>
        )

      default:
        return null
    }
  }

  return (
    <div
      className={cn(
        "p-6 rounded-xl border transition-all duration-200",
        question.completed
          ? "bg-primary/5 border-primary/20"
          : "bg-card border-border/50 hover:border-border"
      )}
    >
      {/* Question Header */}
      <div className="flex items-start gap-3 mb-4">
        {/* Completion Indicator */}
        <div className="mt-1">
          {question.completed ? (
            <CheckCircle2 className="w-5 h-5 text-primary" />
          ) : (
            <Circle className="w-5 h-5 text-muted-foreground" />
          )}
        </div>

        {/* Label and Help Text */}
        <div className="flex-1">
          <label className="block text-sm font-semibold text-foreground mb-1">
            {question.label}
          </label>
          {question.helpText && (
            <div className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <HelpCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>{question.helpText}</span>
            </div>
          )}
          {question.structuredFormat && (
            <div className="mt-2 px-3 py-2 rounded-lg bg-muted/50 border border-border/30">
              <p className="text-xs text-muted-foreground font-mono">
                {question.structuredFormat}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Input Field */}
      <div>{renderInput()}</div>

      {/* Completion Status */}
      {question.completed && question.type !== 'readonly' && (
        <div className="mt-3 flex items-center gap-2 text-xs text-primary">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span className="font-medium">Completed</span>
        </div>
      )}
    </div>
  )
}
