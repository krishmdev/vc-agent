"use client"

import { cn } from "@/lib/utils"
import { BookOpen, ExternalLink, Lightbulb, BarChart3, Users } from "lucide-react"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Resource {
  id: string
  title: string
  type: "article" | "framework" | "example" | "metric"
  description: string
  url?: string
}

interface ResourceSidebarProps {
  resources: Resource[]
  className?: string
}

const typeIcons = {
  article: BookOpen,
  framework: Lightbulb,
  example: Users,
  metric: BarChart3,
}

const typeLabels = {
  article: "Article",
  framework: "Framework",
  example: "Example",
  metric: "Metric",
}

export function ResourceSidebar({ resources, className }: ResourceSidebarProps) {
  return (
    <aside
      className={cn(
        "w-80 bg-card/50 backdrop-blur-sm border-l border-border",
        "flex flex-col",
        className
      )}
    >
      <div className="px-4 py-4 border-b border-border">
        <h3 className="font-semibold text-foreground text-sm">Referenced Resources</h3>
        <p className="text-xs text-muted-foreground mt-1">
          Materials mentioned during your call
        </p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {resources.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-full bg-secondary/50 flex items-center justify-center mx-auto mb-3">
                <BookOpen className="w-5 h-5 text-muted-foreground" />
              </div>
              <p className="text-sm text-muted-foreground">
                Resources will appear here as they are referenced
              </p>
            </div>
          ) : (
            resources.map((resource, index) => {
              const Icon = typeIcons[resource.type]
              return (
                <div
                  key={resource.id}
                  className={cn(
                    "p-3 rounded-xl bg-background border border-border",
                    "transition-all duration-300 hover:border-primary/30 hover:shadow-sm",
                    "animate-in fade-in slide-in-from-right-4"
                  )}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                      <Icon className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                          {typeLabels[resource.type]}
                        </span>
                      </div>
                      <h4 className="text-sm font-medium text-foreground leading-tight mb-1">
                        {resource.title}
                      </h4>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {resource.description}
                      </p>
                      {resource.url && (
                        <a
                          href={resource.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-2"
                        >
                          Learn more
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}
