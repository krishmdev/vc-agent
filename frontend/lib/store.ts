"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"

export type InsightCategory = "problem" | "solution" | "market" | "competition" | "monetization" | "risk" | "customer" | "gtm" | "tech" | "pmf"

export type CardSource = "mentorship" | "vc" | "customer" | null

export interface Insight {
  id: string
  category: InsightCategory
  title: string
  content: string
  timestamp: Date
  source: CardSource
}

export interface ConversationMessage {
  id: string
  role: "user" | "mentor" | "vc" | "customer"
  content: string
  timestamp: Date
}

export interface Resource {
  id: string
  title: string
  type: "article" | "framework" | "example" | "metric"
  url?: string
  description: string
}

export interface FounderProfile {
  name: string
  email: string
  motivation: string
  background: string
}

export interface DashboardCard {
  id: string
  type: "specs" | "customer" | "gtm" | "tech" | "pmf"
  title: string
  content: string
  lastUpdated: Date | null
  lastUpdatedSource: CardSource
}

interface AppState {
  // Idea
  idea: string
  setIdea: (idea: string) => void

  // Founder profile
  founder: FounderProfile
  setFounder: (founder: Partial<FounderProfile>) => void

  // Mentorship conversation
  mentorshipMessages: ConversationMessage[]
  addMentorshipMessage: (message: Omit<ConversationMessage, "id" | "timestamp">) => void
  clearMentorshipMessages: () => void

  // VC conversation
  vcMessages: ConversationMessage[]
  addVcMessage: (message: Omit<ConversationMessage, "id" | "timestamp">) => void

  // Customer conversation
  customerMessages: ConversationMessage[]
  addCustomerMessage: (message: Omit<ConversationMessage, "id" | "timestamp">) => void

  // Insights extracted from conversations
  insights: Insight[]
  addInsight: (insight: Omit<Insight, "id" | "timestamp">) => void
  updateInsightsByCategory: (category: InsightCategory, content: string, source: CardSource) => void
  clearInsights: () => void

  // Dashboard cards
  dashboardCards: DashboardCard[]
  updateDashboardCard: (type: DashboardCard["type"], content: string, source: CardSource) => void

  // Referenced resources
  resources: Resource[]
  addResource: (resource: Omit<Resource, "id">) => void

  // Navigation state
  dashboardUnlocked: boolean
  unlockDashboard: () => void
  
  // Call states
  mentorshipCallCompleted: boolean
  setMentorshipCallCompleted: (completed: boolean) => void
  vcCallCompleted: boolean
  setVcCallCompleted: (completed: boolean) => void
  customerCallCompleted: boolean
  setCustomerCallCompleted: (completed: boolean) => void
}

const defaultDashboardCards: DashboardCard[] = [
  { id: "specs", type: "specs", title: "Product Specs", content: "", lastUpdated: null, lastUpdatedSource: null },
  { id: "customer", type: "customer", title: "Customer Profile", content: "", lastUpdated: null, lastUpdatedSource: null },
  { id: "gtm", type: "gtm", title: "Go-to-Market", content: "", lastUpdated: null, lastUpdatedSource: null },
  { id: "tech", type: "tech", title: "Tech Stack", content: "", lastUpdated: null, lastUpdatedSource: null },
  { id: "pmf", type: "pmf", title: "PMF Signals", content: "", lastUpdated: null, lastUpdatedSource: null },
]

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Idea
      idea: "",
      setIdea: (idea) => set({ idea }),

      // Founder profile
      founder: {
        name: "",
        email: "",
        motivation: "",
        background: "",
      },
      setFounder: (founder) => set((state) => ({ founder: { ...state.founder, ...founder } })),

      // Mentorship conversation
      mentorshipMessages: [],
      addMentorshipMessage: (message) =>
        set((state) => ({
          mentorshipMessages: [
            ...state.mentorshipMessages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: new Date(),
            },
          ],
        })),
      clearMentorshipMessages: () => set({ mentorshipMessages: [] }),

      // VC conversation
      vcMessages: [],
      addVcMessage: (message) =>
        set((state) => ({
          vcMessages: [
            ...state.vcMessages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: new Date(),
            },
          ],
        })),

      // Customer conversation
      customerMessages: [],
      addCustomerMessage: (message) =>
        set((state) => ({
          customerMessages: [
            ...state.customerMessages,
            {
              ...message,
              id: crypto.randomUUID(),
              timestamp: new Date(),
            },
          ],
        })),

      // Insights
      insights: [],
      addInsight: (insight) =>
        set((state) => ({
          insights: [
            ...state.insights,
            {
              ...insight,
              id: crypto.randomUUID(),
              timestamp: new Date(),
            },
          ],
        })),
      updateInsightsByCategory: (category, content, source) =>
        set((state) => {
          const existing = state.insights.find((i) => i.category === category)
          if (existing) {
            return {
              insights: state.insights.map((i) =>
                i.category === category
                  ? { ...i, content, source, timestamp: new Date() }
                  : i
              ),
            }
          }
          return {
            insights: [
              ...state.insights,
              {
                id: crypto.randomUUID(),
                category,
                title: category.charAt(0).toUpperCase() + category.slice(1),
                content,
                source,
                timestamp: new Date(),
              },
            ],
          }
        }),
      clearInsights: () => set({ insights: [] }),

      // Dashboard cards
      dashboardCards: defaultDashboardCards,
      updateDashboardCard: (type, content, source) =>
        set((state) => ({
          dashboardCards: state.dashboardCards.map((card) =>
            card.type === type
              ? { ...card, content, lastUpdated: new Date(), lastUpdatedSource: source }
              : card
          ),
        })),

      // Resources
      resources: [],
      addResource: (resource) =>
        set((state) => ({
          resources: [
            ...state.resources,
            {
              ...resource,
              id: crypto.randomUUID(),
            },
          ],
        })),

      // Navigation
      dashboardUnlocked: false,
      unlockDashboard: () => set({ dashboardUnlocked: true }),

      // Call states
      mentorshipCallCompleted: false,
      setMentorshipCallCompleted: (completed) => set({ mentorshipCallCompleted: completed }),
      vcCallCompleted: false,
      setVcCallCompleted: (completed) => set({ vcCallCompleted: completed }),
      customerCallCompleted: false,
      setCustomerCallCompleted: (completed) => set({ customerCallCompleted: completed }),
    }),
    {
      name: "launchpad-storage",
    }
  )
)
