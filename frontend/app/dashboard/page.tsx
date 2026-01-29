"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
  Lightbulb,
  Users,
  TrendingUp,
  FileText,
  DollarSign,
  User,
  Package,
  Target,
  Cpu,
  Rocket,
  BookOpen,
  ExternalLink,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { BreadcrumbNav } from "@/components/breadcrumb-nav"
import { FounderProfileModal } from "@/components/founder-profile-modal"
import { DashboardCard } from "@/components/dashboard-card"
import { useAppStore } from "@/lib/store"
import { cn } from "@/lib/utils"

export default function DashboardPage() {
  const router = useRouter()
  const {
    idea,
    dashboardUnlocked,
    mentorshipCallCompleted,
    vcCallCompleted,
    customerCallCompleted,
    dashboardCards,
  } = useAppStore()
  const [isVisible, setIsVisible] = useState(false)
  const [isFounderModalOpen, setIsFounderModalOpen] = useState(false)

  useEffect(() => {
    // Redirect if dashboard not unlocked
    if (!dashboardUnlocked) {
      router.push("/")
      return
    }
    setTimeout(() => setIsVisible(true), 50)
  }, [dashboardUnlocked, router])

  if (!dashboardUnlocked) return null

  const cardConfig = [
    { type: "specs" as const, title: "Product Specs", icon: Package },
    { type: "customer" as const, title: "Customer Profile", icon: Users },
    { type: "gtm" as const, title: "Go-to-Market", icon: Rocket },
    { type: "tech" as const, title: "Tech Stack", icon: Cpu },
    { type: "pmf" as const, title: "PMF Signals", icon: Target },
  ]

  const getCardData = (type: string) => {
    return dashboardCards.find((c) => c.type === type) || {
      content: "",
      lastUpdated: null,
      lastUpdatedSource: null,
    }
  }

  return (
    <main className="min-h-screen bg-background">
      {/* Top Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-40 bg-background/80 backdrop-blur-md border-b border-border">
        <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between gap-4">
          {/* Left: Logo + Profile + Call Icons */}
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

      {/* Main Content */}
      <div
        className={cn(
          "pt-24 pb-12 px-4 md:px-6 max-w-6xl mx-auto",
          "transition-all duration-500",
          isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"
        )}
      >
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="font-serif text-3xl md:text-4xl font-semibold text-foreground mb-2">
            Product Dashboard
          </h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Your startup validation hub. Insights update live after each call.
          </p>
        </div>

        {/* Product Overview - Primary Card */}
        <div
          className={cn(
            "mb-8 p-6 rounded-2xl border-2 border-primary/20 bg-gradient-to-br from-primary/5 via-transparent to-transparent",
            "transition-all duration-300 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5"
          )}
        >
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-primary/15 flex items-center justify-center flex-shrink-0">
              <Lightbulb className="w-7 h-7 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-2">
                <h2 className="text-xl font-semibold text-foreground">
                  Product Overview
                </h2>
                {mentorshipCallCompleted && (
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20">
                    Validated
                  </span>
                )}
              </div>
              <p className="text-foreground leading-relaxed text-balance">
                {idea || "No idea captured yet. Complete the mentorship call to populate your product overview."}
              </p>
            </div>
          </div>
        </div>

        {/* Insight Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
          {cardConfig.slice(0, 3).map((config, index) => {
            const cardData = getCardData(config.type)
            return (
              <div
                key={config.type}
                className="animate-in fade-in slide-in-from-bottom-4"
                style={{ animationDelay: `${index * 100}ms`, animationFillMode: "both" }}
              >
                <DashboardCard
                  title={config.title}
                  content={cardData.content}
                  icon={config.icon}
                  lastUpdated={cardData.lastUpdated}
                  lastUpdatedSource={cardData.lastUpdatedSource}
                />
              </div>
            )
          })}
        </div>

        {/* Bottom Row - 2 Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          {cardConfig.slice(3).map((config, index) => {
            const cardData = getCardData(config.type)
            return (
              <div
                key={config.type}
                className="animate-in fade-in slide-in-from-bottom-4"
                style={{ animationDelay: `${(index + 3) * 100}ms`, animationFillMode: "both" }}
              >
                <DashboardCard
                  title={config.title}
                  content={cardData.content}
                  icon={config.icon}
                  lastUpdated={cardData.lastUpdated}
                  lastUpdatedSource={cardData.lastUpdatedSource}
                />
              </div>
            )
          })}
        </div>

        {/* Call to Action Section */}
        <div className="bg-card border border-border rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="w-5 h-5 text-primary" />
            <h2 className="text-lg font-semibold text-foreground">
              Continue Validating
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* VC Call CTA */}
            <button
              onClick={() => router.push("/vc-call")}
              className={cn(
                "relative p-5 rounded-xl border text-left transition-all duration-300",
                "hover:shadow-md hover:border-primary/30 group",
                vcCallCompleted
                  ? "bg-secondary/30 border-border"
                  : "bg-gradient-to-br from-amber-500/5 to-transparent border-amber-500/20"
              )}
            >
              {!vcCallCompleted && (
                <span className="absolute top-3 right-3 w-2.5 h-2.5 bg-primary rounded-full animate-pulse" />
              )}
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center transition-colors",
                    vcCallCompleted
                      ? "bg-muted"
                      : "bg-amber-500/10 group-hover:bg-amber-500/20"
                  )}
                >
                  <DollarSign
                    className={cn(
                      "w-6 h-6",
                      vcCallCompleted ? "text-muted-foreground" : "text-amber-600"
                    )}
                  />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground mb-1">
                    VC Call
                    {vcCallCompleted && (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        Completed
                      </span>
                    )}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Simulate a pitch meeting with investor-style questions
                  </p>
                </div>
              </div>
            </button>

            {/* Customer Call CTA */}
            <button
              onClick={() => router.push("/customer-call")}
              className={cn(
                "relative p-5 rounded-xl border text-left transition-all duration-300",
                "hover:shadow-md hover:border-primary/30 group",
                customerCallCompleted
                  ? "bg-secondary/30 border-border"
                  : "bg-gradient-to-br from-blue-500/5 to-transparent border-blue-500/20"
              )}
            >
              {!customerCallCompleted && (
                <span className="absolute top-3 right-3 w-2.5 h-2.5 bg-primary rounded-full animate-pulse" />
              )}
              <div className="flex items-start gap-4">
                <div
                  className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center transition-colors",
                    customerCallCompleted
                      ? "bg-muted"
                      : "bg-blue-500/10 group-hover:bg-blue-500/20"
                  )}
                >
                  <Users
                    className={cn(
                      "w-6 h-6",
                      customerCallCompleted ? "text-muted-foreground" : "text-blue-600"
                    )}
                  />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground mb-1">
                    Customer Call
                    {customerCallCompleted && (
                      <span className="ml-2 text-xs font-normal text-muted-foreground">
                        Completed
                      </span>
                    )}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Validate assumptions with customer discovery
                  </p>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </main>
  )
}
