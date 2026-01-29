"use client"

import type { LucideIcon } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { CardSource } from "@/lib/store"

interface DashboardCardProps {
  title: string
  content: string
  icon: LucideIcon
  lastUpdated?: Date | null
  lastUpdatedSource?: CardSource
  isPrimary?: boolean
  className?: string
}

function formatTimeAgo(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - new Date(date).getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return "just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

function getSourceLabel(source: CardSource): string {
  switch (source) {
    case "mentorship":
      return "Updated from Mentorship Call"
    case "vc":
      return "Updated from VC Call"
    case "customer":
      return "Updated from Customer Call"
    default:
      return ""
  }
}

function getSourceColor(source: CardSource): string {
  switch (source) {
    case "mentorship":
      return "bg-primary/10 text-primary border-primary/20"
    case "vc":
      return "bg-amber-500/10 text-amber-600 border-amber-500/20"
    case "customer":
      return "bg-blue-500/10 text-blue-600 border-blue-500/20"
    default:
      return "bg-muted text-muted-foreground border-border"
  }
}

export function DashboardCard({
  title,
  content,
  icon: Icon,
  lastUpdated,
  lastUpdatedSource,
  isPrimary = false,
  className,
}: DashboardCardProps) {
  const hasUpdate = lastUpdated && lastUpdatedSource

  return (
    <Card
      className={cn(
        "transition-all duration-300 hover:shadow-md group relative overflow-hidden",
        isPrimary 
          ? "border-primary/30 bg-gradient-to-br from-primary/5 to-transparent" 
          : "hover:border-primary/20",
        className
      )}
    >
      {/* Update badge */}
      {hasUpdate && (
        <div 
          className={cn(
            "absolute top-3 right-3 px-2 py-1 rounded-full text-xs font-medium border",
            getSourceColor(lastUpdatedSource)
          )}
        >
          {formatTimeAgo(lastUpdated)}
        </div>
      )}

      <CardHeader className="pb-2">
        <div className="flex items-start gap-3">
          <div 
            className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors",
              isPrimary 
                ? "bg-primary/20 text-primary" 
                : "bg-secondary text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary"
            )}
          >
            <Icon className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-base font-semibold text-foreground">
              {title}
            </CardTitle>
            {hasUpdate && (
              <p className="text-xs text-muted-foreground mt-0.5">
                {getSourceLabel(lastUpdatedSource)}
              </p>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {content ? (
          <p className="text-sm text-muted-foreground leading-relaxed line-clamp-4">
            {content}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground/60 italic">
            No insights yet. Complete a call to populate this section.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
