"use client"

import { ModuleId } from "@/lib/dashboard-types"
import { sequoiaResources } from "@/lib/dashboard-data"
import { cn } from "@/lib/utils"
import { FileText, Box, BookOpen, Lightbulb, ExternalLink } from "lucide-react"

interface ResourceSidebarDashboardProps {
  moduleId: ModuleId | null
  activeQuestionId?: string | null
}

const resourceIcons = {
  article: FileText,
  framework: Box,
  example: BookOpen,
  guidance: Lightbulb,
}

export function ResourceSidebarDashboard({ moduleId, activeQuestionId }: ResourceSidebarDashboardProps) {
  // Filter resources for the current module
  const relevantResources = moduleId
    ? sequoiaResources.filter((resource) => resource.moduleId === moduleId)
    : []

  // Further filter by active question if specified
  const displayedResources = activeQuestionId
    ? relevantResources.filter(
        (resource) =>
          !resource.questionIds || resource.questionIds.includes(activeQuestionId)
      )
    : relevantResources

  if (!moduleId || displayedResources.length === 0) {
    return (
      <div className="hidden lg:flex w-80 shrink-0 bg-card border-l border-border/50 flex-col h-full">
        <div className="p-6 border-b border-border/50">
          <h3 className="font-semibold text-sm text-foreground">Sequoia Resources</h3>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-full bg-muted/50 flex items-center justify-center mx-auto">
              <FileText className="w-6 h-6 text-muted-foreground" />
            </div>
            <p className="text-sm text-muted-foreground">
              Select a module to view relevant resources
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="hidden lg:flex w-80 shrink-0 bg-card border-l border-border/50 flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-border/50">
        <div className="flex items-center gap-2 mb-1">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <BookOpen className="w-4 h-4 text-primary" />
          </div>
          <h3 className="font-semibold text-sm text-foreground">Sequoia Resources</h3>
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          Guidance from top venture capital insights
        </p>
      </div>

      {/* Resources List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          {displayedResources.map((resource, index) => {
            const Icon = resourceIcons[resource.type]
            return (
              <div
                key={resource.id}
                className={cn(
                  "p-4 rounded-xl bg-background border border-border/50",
                  "hover:shadow-md hover:border-primary/20 transition-all duration-200",
                  "animate-in fade-in-0 slide-in-from-right-4"
                )}
                style={{
                  animationDelay: `${index * 100}ms`,
                  animationFillMode: "backwards",
                }}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                    <Icon className="w-4 h-4 text-primary" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h4 className="font-semibold text-sm text-foreground leading-tight">
                        {resource.title}
                      </h4>
                      {resource.url && (
                        <ExternalLink className="w-3.5 h-3.5 text-muted-foreground shrink-0 mt-0.5" />
                      )}
                    </div>

                    {/* Type Badge */}
                    <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 mb-2">
                      <span className="text-xs font-medium text-primary capitalize">
                        {resource.type}
                      </span>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      {resource.description}
                    </p>

                    {/* Link */}
                    {resource.url && (
                      <a
                        href={resource.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 mt-3 text-xs font-medium text-primary hover:underline"
                      >
                        View Resource
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border/50">
        <p className="text-xs text-muted-foreground leading-relaxed">
          These resources are curated from Sequoia Capital&apos;s pitch deck guidance and
          investment framework
        </p>
      </div>
    </div>
  )
}
