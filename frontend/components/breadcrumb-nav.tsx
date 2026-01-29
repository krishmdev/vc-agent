"use client"

import React from "react"

import Link from "next/link"
import { ChevronRight, Lightbulb, MessageSquare, LayoutDashboard } from "lucide-react"
import { cn } from "@/lib/utils"

interface BreadcrumbStep {
  id: string
  label: string
  icon: React.ReactNode
  href?: string
  current?: boolean
  completed?: boolean
}

interface BreadcrumbNavProps {
  currentStep: "idea" | "mentorship" | "dashboard"
  className?: string
}

export function BreadcrumbNav({ currentStep, className }: BreadcrumbNavProps) {
  const steps: BreadcrumbStep[] = [
    {
      id: "idea",
      label: "Idea",
      icon: <Lightbulb className="w-3.5 h-3.5" />,
      href: "/",
      current: currentStep === "idea",
      completed: currentStep !== "idea",
    },
    {
      id: "mentorship",
      label: "Mentorship",
      icon: <MessageSquare className="w-3.5 h-3.5" />,
      href: "/mentorship",
      current: currentStep === "mentorship",
      completed: currentStep === "dashboard",
    },
    {
      id: "dashboard",
      label: "Dashboard",
      icon: <LayoutDashboard className="w-3.5 h-3.5" />,
      href: "/dashboard",
      current: currentStep === "dashboard",
      completed: false,
    },
  ]

  return (
    <nav className={cn("flex items-center", className)} aria-label="Breadcrumb">
      <ol className="flex items-center gap-1">
        {steps.map((step, index) => (
          <li key={step.id} className="flex items-center">
            {step.href && !step.current ? (
              <Link
                href={step.href}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
                  step.completed 
                    ? "text-primary/80 hover:text-primary hover:bg-primary/5" 
                    : "text-muted-foreground hover:text-foreground hover:bg-secondary"
                )}
              >
                {step.icon}
                <span className="hidden sm:inline">{step.label}</span>
              </Link>
            ) : (
              <span
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-200",
                  step.current && "bg-primary/10 text-primary"
                )}
              >
                {step.icon}
                <span>{step.label}</span>
              </span>
            )}
            
            {index < steps.length - 1 && (
              <ChevronRight 
                className={cn(
                  "w-4 h-4 mx-0.5 flex-shrink-0",
                  step.completed ? "text-primary/40" : "text-muted-foreground/30"
                )} 
              />
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}
