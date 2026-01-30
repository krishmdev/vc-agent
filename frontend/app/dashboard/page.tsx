"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  FileText,
  DollarSign,
  User,
  Users,
  BookOpen,
  ExternalLink,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { BreadcrumbNav } from "@/components/breadcrumb-nav"
import { FounderProfileModal } from "@/components/founder-profile-modal"
import { ModuleSidebar } from "@/components/module-sidebar"
import { ModuleContent } from "@/components/module-content"
import { ResourceSidebarDashboard } from "@/components/resource-sidebar-dashboard"
import { useAppStore } from "@/lib/store"
import { ModuleId } from "@/lib/dashboard-types"
import { cn } from "@/lib/utils"

export default function DashboardPage() {
  const router = useRouter()
  const {
    dashboardUnlocked,
    vcCallCompleted,
    customerCallCompleted,
    modules,
    expandedModuleId,
    setExpandedModule,
    calculateGlobalProgress,
  } = useAppStore()

  const [isVisible, setIsVisible] = useState(false)
  const [isFounderModalOpen, setIsFounderModalOpen] = useState(false)
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null)

  const globalProgress = calculateGlobalProgress()

  useEffect(() => {
    // Redirect if dashboard not unlocked
    if (!dashboardUnlocked) {
      router.push("/")
      return
    }

    // Set default expanded module to first one (founder)
    if (!expandedModuleId) {
      setExpandedModule('founder')
    }

    setTimeout(() => setIsVisible(true), 50)
  }, [dashboardUnlocked, router, expandedModuleId, setExpandedModule])

  if (!dashboardUnlocked) return null

  const handleModuleClick = (moduleId: ModuleId) => {
    setExpandedModule(moduleId)
    setActiveQuestionId(null) // Reset active question when switching modules
  }

  const handleQuestionFocus = (questionId: string) => {
    setActiveQuestionId(questionId)
  }

  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-40 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="h-16 px-4 md:px-6 flex items-center justify-between gap-4">
          {/* Left: Profile + Call Icons */}
          <div className="flex items-center gap-3">
            {/* Founder Profile */}
            <button
              onClick={() => setIsFounderModalOpen(true)}
              className="relative w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center hover:bg-primary/20 transition-colors"
              aria-label="Founder profile"
            >
              <User className="w-4 h-4 text-primary" />
            </button>

            {/* Divider */}
            <div className="w-px h-6 bg-border" />

            {/* VC Call */}
            <button
              onClick={() => router.push("/vc-call")}
              className="relative flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-secondary transition-colors group"
              aria-label="VC Call"
            >
              <DollarSign className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
              <span className="text-sm text-muted-foreground group-hover:text-foreground hidden sm:inline">
                VC Call
              </span>
              {!vcCallCompleted && (
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-primary rounded-full ring-2 ring-background" />
              )}
            </button>

            {/* Customer Call */}
            <button
              onClick={() => router.push("/customer-call")}
              className="relative flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-secondary transition-colors group"
              aria-label="Customer Call"
            >
              <Users className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
              <span className="text-sm text-muted-foreground group-hover:text-foreground hidden sm:inline">
                Customer Call
              </span>
              {!customerCallCompleted && (
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-primary rounded-full ring-2 ring-background" />
              )}
            </button>
          </div>

          {/* Center: Breadcrumb */}
          <BreadcrumbNav currentStep="dashboard" />

          {/* Right: Resources + Investor Memo */}
          <div className="flex items-center gap-2">
            <Link
              href="https://www.sequoiacap.com/article/writing-a-business-plan/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            >
              <BookOpen className="w-4 h-4" />
              <span className="hidden md:inline">Resources</span>
              <ExternalLink className="w-3 h-3 opacity-50" />
            </Link>

            <Button
              onClick={() => router.push("/investor-memo")}
              size="sm"
              className="gap-2"
              disabled={globalProgress < 100}
            >
              <FileText className="w-4 h-4" />
              <span className="hidden sm:inline">Investor Memo</span>
            </Button>
          </div>
        </div>
      </nav>

      {/* Founder Profile Modal */}
      <FounderProfileModal
        isOpen={isFounderModalOpen}
        onClose={() => setIsFounderModalOpen(false)}
      />

      {/* Three-Column Layout */}
      <div
        className={cn(
          "flex-1 flex mt-16 transition-all duration-500",
          isVisible ? "opacity-100" : "opacity-0"
        )}
      >
        {/* Left Sidebar - Module Navigation */}
        <ModuleSidebar onModuleClick={handleModuleClick} />

        {/* Center - Module Content */}
        <div className="flex-1 bg-background overflow-hidden">
          {expandedModuleId ? (
            <ModuleContent
              module={modules[expandedModuleId]}
              moduleId={expandedModuleId}
              onQuestionFocus={handleQuestionFocus}
            />
          ) : (
            <div className="h-full flex items-center justify-center p-8">
              <div className="text-center space-y-4 max-w-md">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
                  <FileText className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-semibold text-foreground">
                  Welcome to Your Product Dashboard
                </h2>
                <p className="text-muted-foreground">
                  Select a module from the left sidebar to begin structuring your startup
                  validation journey. Complete each section to build an investor-grade
                  narrative.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar - Sequoia Resources */}
        <ResourceSidebarDashboard
          moduleId={expandedModuleId}
          activeQuestionId={activeQuestionId}
        />
      </div>
    </main>
  )
}
