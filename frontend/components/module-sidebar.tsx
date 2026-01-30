"use client"

import { ModuleId } from "@/lib/dashboard-types"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import * as LucideIcons from "lucide-react"

interface ModuleSidebarProps {
  onModuleClick: (moduleId: ModuleId) => void
}

export function ModuleSidebar({ onModuleClick }: ModuleSidebarProps) {
  const { modules, expandedModuleId, calculateGlobalProgress } = useAppStore()
  const globalProgress = calculateGlobalProgress()

  const moduleOrder: ModuleId[] = ['founder', 'problem', 'customer', 'product', 'market']

  return (
    <div className="w-64 bg-card border-r border-border/50 flex flex-col h-full">
      {/* Global Progress */}
      <div className="p-6 border-b border-border/50">
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-muted-foreground">Overall Progress</span>
            <span className="font-semibold text-foreground">{globalProgress}%</span>
          </div>
          <div className="h-2 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-primary/80 transition-all duration-500 ease-out"
              style={{ width: `${globalProgress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Module Navigation */}
      <nav className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {moduleOrder.map((moduleId, index) => {
            const module = modules[moduleId]
            const isExpanded = expandedModuleId === moduleId
            const IconComponent = (LucideIcons as any)[module.icon] || LucideIcons.Circle

            return (
              <button
                key={moduleId}
                onClick={() => onModuleClick(moduleId)}
                className={cn(
                  "w-full text-left rounded-xl p-4 transition-all duration-200",
                  "hover:bg-muted/50 hover:shadow-sm",
                  "focus:outline-none focus:ring-2 focus:ring-primary/20",
                  isExpanded && "bg-primary/5 shadow-sm ring-2 ring-primary/20"
                )}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <div
                    className={cn(
                      "flex items-center justify-center w-8 h-8 rounded-lg transition-colors shrink-0",
                      isExpanded
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    <IconComponent className="w-4 h-4" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={cn(
                          "font-semibold text-sm",
                          isExpanded ? "text-foreground" : "text-foreground/80"
                        )}
                      >
                        {module.title}
                      </span>
                      {module.completionPercentage === 100 && (
                        <LucideIcons.CheckCircle2 className="w-4 h-4 text-primary shrink-0" />
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                      {module.description}
                    </p>

                    {/* Progress Bar */}
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                        <div
                          className={cn(
                            "h-full transition-all duration-300 rounded-full",
                            module.completionPercentage === 100
                              ? "bg-primary"
                              : "bg-primary/60"
                          )}
                          style={{ width: `${module.completionPercentage}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-muted-foreground shrink-0">
                        {module.completionPercentage}%
                      </span>
                    </div>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border/50">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <LucideIcons.Target className="w-4 h-4" />
          <span>Complete all modules to generate your investor memo</span>
        </div>
      </div>
    </div>
  )
}
