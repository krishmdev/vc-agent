"use client"

import { useEffect, useState, useRef } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  FileText,
  DollarSign,
  User,
  Users,
  BookOpen,
  ExternalLink,
  Loader2,
  RefreshCw,
  Presentation,
  Target,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { BreadcrumbNav } from "@/components/breadcrumb-nav"
import { FounderProfileModal } from "@/components/founder-profile-modal"
import { FloatingMentorButton } from "@/components/floating-mentor-button"
import { ModuleSidebar } from "@/components/module-sidebar"
import { ModuleContent } from "@/components/module-content"
import { ResourceSidebarDashboard } from "@/components/resource-sidebar-dashboard"
import { useAppStore } from "@/lib/store"
import { ModuleId } from "@/lib/dashboard-types"
import { cn } from "@/lib/utils"
import { ResearchAgentIcon } from "@/components/research-agent-icon"
import { ResearchChat } from "@/components/research-chat"
import { ResourceDrawer } from "@/components/resource-drawer"
import { CustomerReachoutPopup } from "@/components/customer-reachout-popup"
import { CustomerResultsModal } from "@/components/customer-results-modal"

import { VCReportModal } from "@/components/vc-report-modal"
import { VCFeedbackCard } from "@/components/vc-feedback-card"

export default function DashboardPage() {
  const router = useRouter()
  const {
    dashboardUnlocked,
    vcCallCompleted,
    vcReport,
    customerCallCompleted,
    modules,
    expandedModuleId,
    setExpandedModule,
    calculateGlobalProgress,
    autofillFromMemories,
    isAutofilling,
  } = useAppStore()



  const [isVisible, setIsVisible] = useState(false)
  const [isFounderModalOpen, setIsFounderModalOpen] = useState(false)
  const [isReportModalOpen, setIsReportModalOpen] = useState(false)
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null)

  // Research Agent State
  const [isResearchOpen, setIsResearchOpen] = useState(false)
  const [initialContext, setInitialContext] = useState<{ idea?: string, problem?: string, customer?: string, product?: string } | undefined>(undefined)

  // Customer Reach-out State
  const [isReachOutPopupOpen, setIsReachOutPopupOpen] = useState(false)
  const [isResultsModalOpen, setIsResultsModalOpen] = useState(false)
  const [isSearching, setIsSearching] = useState(false)
  const [searchResult, setSearchResult] = useState<any>(null)
  const [searchIcp, setSearchIcp] = useState("")
  const [searchType, setSearchType] = useState<"B2C" | "B2B">("B2C")
  const customerButtonRef = useRef<HTMLDivElement>(null)



  const globalProgress = calculateGlobalProgress()

  // Compute context for Research Agent
  useEffect(() => {
    if (!dashboardUnlocked) return;

    const getAnswer = (moduleId: ModuleId, questionIds: string[]) => {
      const module = modules[moduleId];
      if (!module) return null;

      // Search through all subsections
      for (const sub of module.subsections) {
        for (const q of sub.questions) {
          if (questionIds.includes(q.id)) {
            // Return first non-empty value if found
            if (Array.isArray(q.value)) {
              if (q.value.length > 0) return q.value.join(", ");
            } else if (q.value) {
              return q.value;
            }
          }
        }
      }
      return null;
    };

    const idea = sessionStorage.getItem("startup-idea") || undefined;
    const problem = getAnswer('problem', ['problem-formula', 'problem-breaks']) || undefined;
    const customer = getAnswer('customer', ['early-adopters', 'customer-description']) || undefined;
    const product = getAnswer('product', ['product-description', 'company-purpose']) || undefined;

    setInitialContext({ idea, problem, customer, product });
  }, [modules, dashboardUnlocked]);

  useEffect(() => {
    // Redirect if dashboard not unlocked
    if (!dashboardUnlocked) {
      router.push("/")
      return
    }

    if (!expandedModuleId) {
      setExpandedModule('founder')
    }

    // Poll for report if not present (Long Polling)
    if (!vcReport) {
      // Single separate async check to avoid blocking UI
      const checkReport = async () => {
        try {
          // This request will hang (long poll) on the server until report is ready or timeout
          const res = await fetch('/api/vc-report');
          const data = await res.json();
          if (data.exists && data.report) {
            // Update store
            useAppStore.getState().setVcReport(data.report);
                    
                    // Auto-fill modules with extracted data
                    if (data.report.extraction) {
                         useAppStore.getState().autoFillModules(data.report.extraction);
                    }
          }
        } catch (e) {
          // ignore
        }
      };

      checkReport();
    }

    // Auto-open report if available and we just came back
    if (vcReport && !isReportModalOpen) {
      // Optional: auto-open logic
    }

    setTimeout(() => setIsVisible(true), 50)
  }, [dashboardUnlocked, router, expandedModuleId, setExpandedModule, vcReport])

  if (!dashboardUnlocked) return null

  const handleModuleClick = (moduleId: ModuleId) => {
    setExpandedModule(moduleId)
    setActiveQuestionId(null) // Reset active question when switching modules
  }

  const handleQuestionFocus = (questionId: string) => {
    setActiveQuestionId(questionId)
  }

  const handleStartResearch = async () => {
    // No usage, component state initialization handled in useEffect
  }

  const handleFindCustomers = async (icp: string, type: "B2C" | "B2B") => {
    setSearchIcp(icp)
    setSearchType(type)
    setIsReachOutPopupOpen(false)
    setIsResultsModalOpen(true)
    setIsSearching(true)
    setSearchResult(null)

    try {
      const res = await fetch('/api/customer-reachout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ icp_description: icp, customer_type: type })
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("API Error details:", errorText);
        throw new Error(`Start failed: ${res.status} ${res.statusText} - ${errorText}`);
      }

      const { task_id } = await res.json();

      // Polling
      const poll = setInterval(async () => {
        try {
          const pollRes = await fetch(`/api/customer-reachout?taskId=${task_id}`);
          const data = await pollRes.json();

          if (data.status === 'completed') {
            setSearchResult(data.content);
            setIsSearching(false);
            clearInterval(poll);
          } else if (data.status === 'failed') {
            console.error("Task failed", data.error);
            setIsSearching(false);
            clearInterval(poll);
          }
        } catch (e) {
          console.error("Polling error", e);
          clearInterval(poll);
        }
      }, 2000);

    } catch (error) {
      console.error("Search failed", error);
      setIsSearching(false);
    }
  }

  const handleRefineSearch = () => {
    setIsResultsModalOpen(false)
    setIsReachOutPopupOpen(true)
  }



  return (
    <main className="min-h-screen bg-background flex flex-col">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-40 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="h-16 px-4 md:px-6 flex items-center justify-between gap-4">
          {/* Left: Profile + Call Icons */}
          <div className="flex items-center gap-3">
            {/* Research Agent */}
            <ResearchAgentIcon onClick={() => setIsResearchOpen(true)} />

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
                {vcCallCompleted ? "Retake Pitch" : "VC Call"}
              </span>
              {!vcCallCompleted && (
                <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-primary rounded-full ring-2 ring-background" />
              )}
            </button>

            {/* VC Feedback Button */}
            {vcReport && (
              <button
                onClick={() => setIsReportModalOpen(true)}
                className="relative flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-secondary transition-colors group text-indigo-600 dark:text-indigo-400"
                aria-label="View VC Feedback"
              >
                <Target className="w-4 h-3" />
                <span className="text-sm font-medium hidden sm:inline">
                  View Feedback
                </span>
              </button>
            )}

            {/* Customer Reach-out */}
            <div className="relative" ref={customerButtonRef}>
              <button
                onClick={() => setIsReachOutPopupOpen(!isReachOutPopupOpen)}
                className={cn(
                  "relative flex items-center gap-2 px-3 py-1.5 rounded-full hover:bg-secondary transition-colors group",
                  isReachOutPopupOpen && "bg-secondary"
                )}
                aria-label="Customer Reach-out"
              >
                <Users className="w-4 h-4 text-muted-foreground group-hover:text-foreground" />
                <span className="text-sm text-muted-foreground group-hover:text-foreground hidden sm:inline">
                  Customer Reach-out
                </span>
                {!customerCallCompleted && (
                  <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-primary rounded-full ring-2 ring-background" />
                )}
              </button>

              <CustomerReachoutPopup
                isOpen={isReachOutPopupOpen}
                onClose={() => setIsReachOutPopupOpen(false)}
                onFindCustomers={handleFindCustomers}
                anchorRef={customerButtonRef}
              />
            </div>
          </div>
          {/* Center: Breadcrumb */}
          <BreadcrumbNav currentStep="dashboard" />

          {/* Right: Sync + Resources + Investor Memo */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => autofillFromMemories()}
              disabled={isAutofilling}
              className="gap-2"
            >
              {isAutofilling ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              <span className="hidden md:inline">
                {isAutofilling ? "Syncing..." : "Sync Voice Chat"}
              </span>
            </Button>
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
              className={cn(
                "gap-2 transition-all duration-500",
                vcReport ? "bg-green-600 hover:bg-green-700 text-white shadow-lg animate-pulse" : ""
              )}
            >
              <FileText className="w-4 h-4" />
              <span className="hidden sm:inline">
                {vcReport ? "View Investor Memo (Unocked)" : "Investor Memo"}
              </span>
            </Button>
          </div>
        </div>
      </nav>

      {/* Founder Profile Modal */}
      <FounderProfileModal
        isOpen={isFounderModalOpen}
        onClose={() => setIsFounderModalOpen(false)}
      />

      <ResearchChat
        isOpen={isResearchOpen}
        onClose={() => setIsResearchOpen(false)}
        initialContext={initialContext}
      />

      <CustomerResultsModal
        isOpen={isResultsModalOpen}
        onClose={() => setIsResultsModalOpen(false)}
        isLoading={isSearching}
        customerType={searchType}
        icpDescription={searchIcp}
        results={searchResult}
        onRefine={handleRefineSearch}
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
        <div className="flex-1 bg-background overflow-hidden flex flex-col">
          {/* VC Feedback Banner */}
          {vcReport && (
            <div className="p-6 pb-0">
              <VCFeedbackCard report={vcReport} />
            </div>
          )}

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

      {/* Floating Mentor Call Button */}
      <FloatingMentorButton />

      {/* Resource Drawer */}
      <ResourceDrawer />



      <VCReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        report={vcReport}
      />
    </main>
  )
}
