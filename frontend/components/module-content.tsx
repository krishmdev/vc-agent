"use client"

import { Module, ModuleId } from "@/lib/dashboard-types"
import { QuestionCard } from "./question-card"
import { cn } from "@/lib/utils"
import * as LucideIcons from "lucide-react"
import { useState } from "react"

interface ModuleContentProps {
  module: Module
  moduleId: ModuleId
  onQuestionFocus?: (questionId: string) => void
}

export function ModuleContent({ module, moduleId, onQuestionFocus }: ModuleContentProps) {
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null)
  const IconComponent = (LucideIcons as any)[module.icon] || LucideIcons.Circle

  const handleQuestionFocus = (questionId: string) => {
    setActiveQuestionId(questionId)
    onQuestionFocus?.(questionId)
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto p-8">
        {/* Module Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
              <IconComponent className="w-6 h-6 text-primary" />
            </div>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-foreground mb-1">{module.title}</h1>
              <p className="text-sm text-muted-foreground">{module.description}</p>
            </div>
            {/* Progress Badge */}
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10">
              <span className="text-sm font-semibold text-primary">
                {module.completionPercentage}%
              </span>
              {module.completionPercentage === 100 && (
                <LucideIcons.CheckCircle2 className="w-4 h-4 text-primary" />
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-primary/80 transition-all duration-500"
              style={{ width: `${module.completionPercentage}%` }}
            />
          </div>
        </div>

        {/* Subsections */}
        <div className="space-y-8">
          {module.subsections.map((subsection, subsectionIndex) => {
            const allQuestionsCompleted = subsection.questions
              .filter(q => q.type !== 'readonly')
              .every(q => q.completed)

            return (
              <div
                key={subsection.id}
                className={cn(
                  "animate-in fade-in-0 slide-in-from-bottom-4",
                )}
                style={{
                  animationDelay: `${subsectionIndex * 100}ms`,
                  animationFillMode: "backwards",
                }}
              >
                {/* Subsection Header */}
                <div className="mb-6">
                  <div className="flex items-center gap-3 mb-2">
                    <h2 className="text-lg font-semibold text-foreground">
                      {subsection.title}
                    </h2>
                    {allQuestionsCompleted && subsection.questions.length > 0 && (
                      <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10">
                        <LucideIcons.CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                        <span className="text-xs font-medium text-primary">Complete</span>
                      </div>
                    )}
                  </div>
                  {subsection.description && (
                    <p className="text-sm text-muted-foreground">{subsection.description}</p>
                  )}
                </div>

                {/* Questions */}
                <div className="space-y-4">
                  {subsection.questions.map((question) => (
                    <QuestionCard
                      key={question.id}
                      question={question}
                      moduleId={moduleId}
                      onFocus={() => handleQuestionFocus(question.id)}
                    />
                  ))}
                </div>
              </div>
            )
          })}
        </div>

        {/* Module Footer */}
        {module.completionPercentage === 100 && (
          <div className="mt-8 p-6 rounded-xl bg-primary/5 border border-primary/20">
            <div className="flex items-center gap-3">
              <LucideIcons.CheckCircle2 className="w-6 h-6 text-primary" />
              <div>
                <h3 className="font-semibold text-foreground mb-1">
                  {module.title} Module Complete
                </h3>
                <p className="text-sm text-muted-foreground">
                  Great work! Continue to the next module or refine your answers.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
