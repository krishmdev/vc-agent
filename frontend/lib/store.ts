"use client"

import { create } from "zustand"
import { persist } from "zustand/middleware"
import { Module, ModuleId, Question } from "./dashboard-types"
import { initialModules } from "./dashboard-data"

export type InsightCategory = "problem" | "solution" | "market" | "competition" | "monetization" | "risk" | "customer" | "gtm" | "tech" | "pmf"

export type CardSource = "mentorship" | "vc" | "customer" | null

export interface VCReport {
  diagnosis: string
  strengths: string[]
  gaps: string[]
  terrifyingQuestions: string[]
  nextSteps: string[]
  extraction: Record<string, string> // New field for auto-filling modules
}

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

export interface AppState {
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
  vcReport: VCReport | null
  setVcReport: (report: VCReport) => void

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

  // New structured dashboard
  modules: Record<ModuleId, Module>
  activeModuleId: ModuleId | null
  expandedModuleId: ModuleId | null
  resourceSidebarOpen: boolean
  activeResourceQuestionId: string | null
  setActiveModule: (moduleId: ModuleId | null) => void
  setExpandedModule: (moduleId: ModuleId | null) => void
  toggleResourceSidebar: (isOpen: boolean) => void
  setActiveResourceQuestion: (questionId: string | null) => void
  updateQuestion: (moduleId: ModuleId, questionId: string, value: string | string[]) => void
  calculateModuleProgress: (moduleId: ModuleId) => number
  calculateGlobalProgress: () => number
  autofillFromMemories: () => Promise<void>
  isAutofilling: boolean
  // Fill empty answers from a VC report's extraction ({ questionId: text })
  autoFillModules: (extraction: Record<string, string>) => void
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
    (set, get) => ({
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
      vcReport: null,
      setVcReport: (report) => set({ vcReport: report }),

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

      // New structured dashboard
      modules: initialModules,
      activeModuleId: null,
      expandedModuleId: null,
      resourceSidebarOpen: false,
      activeResourceQuestionId: null,

      setActiveModule: (moduleId) => set({ activeModuleId: moduleId }),

      setExpandedModule: (moduleId) => set({ expandedModuleId: moduleId }),

      toggleResourceSidebar: (isOpen) => set({ resourceSidebarOpen: isOpen }),

      setActiveResourceQuestion: (questionId) => set({ activeResourceQuestionId: questionId }),

      updateQuestion: (moduleId, questionId, value) =>
        set((state) => {
          const mod = state.modules[moduleId]
          const updatedSubsections = mod.subsections.map((subsection) => ({
            ...subsection,
            questions: subsection.questions.map((question) =>
              question.id === questionId
                ? {
                  ...question,
                  value,
                  completed: Array.isArray(value)
                    ? value.some(v => v.trim().length > 0)
                    : typeof value === 'string' && value.trim().length > 0,
                }
                : question
            ),
          }))

          const updatedModule = {
            ...module,
            subsections: updatedSubsections,
          }

          // Calculate progress for this module
          const allQuestions = updatedSubsections.flatMap(s => s.questions).filter(q => q.type !== 'readonly')
          const completedQuestions = allQuestions.filter(q => q.completed)
          const completionPercentage = allQuestions.length > 0
            ? Math.round((completedQuestions.length / allQuestions.length) * 100)
            : 0

          return {
            modules: {
              ...state.modules,
              [moduleId]: {
                ...updatedModule,
                completionPercentage,
              },
            },
          }
        }),

      calculateModuleProgress: (moduleId) => {
        const state = get()
        const mod = state.modules[moduleId]
        const allQuestions = mod.subsections
          .flatMap(s => s.questions)
          .filter(q => q.type !== 'readonly')
        const completedQuestions = allQuestions.filter(q => q.completed)
        return allQuestions.length > 0
          ? Math.round((completedQuestions.length / allQuestions.length) * 100)
          : 0
      },

      calculateGlobalProgress: () => {
        const state = get()
        const moduleIds: ModuleId[] = ['founder', 'problem', 'customer', 'product', 'market']
        const totalProgress = moduleIds.reduce((sum, id) => {
          return sum + state.modules[id].completionPercentage
        }, 0)
        return Math.round(totalProgress / moduleIds.length)
      },

      autoFillModules: (extraction) => {
        const { modules, updateQuestion } = get()
        for (const [questionId, value] of Object.entries(extraction || {})) {
          if (!value || !value.trim()) continue
          for (const [moduleId, mod] of Object.entries(modules) as [ModuleId, Module][]) {
            const question = mod.subsections.flatMap((s) => s.questions).find((q) => q.id === questionId)
            if (question && !question.value) updateQuestion(moduleId, questionId, value)
          }
        }
      },

      // Autofill from Mem0 memories
      isAutofilling: false,
      autofillFromMemories: async () => {
        set({ isAutofilling: true })
        try {
          // Step 1: Fetch memories from Mem0
          console.log('[AUTOFILL] Fetching memories...')
          const memoriesRes = await fetch('/api/memories')
          const memoriesData = await memoriesRes.json()

          if (!memoriesData.memories || memoriesData.memories.length === 0) {
            console.log('[AUTOFILL] No memories found')
            set({ isAutofilling: false })
            return
          }
          console.log(`[AUTOFILL] Found ${memoriesData.memories.length} memories`)

          // Step 2: Extract fields using Gemini
          console.log('[AUTOFILL] Extracting fields...')
          const extractRes = await fetch('/api/extract-fields', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ memories: memoriesData.memories })
          })
          const extractData = await extractRes.json()

          console.log('[AUTOFILL] Extract response:', JSON.stringify(extractData))

          if (!extractData.fields || extractData.fields.length === 0) {
            console.log('[AUTOFILL] No fields extracted')
            set({ isAutofilling: false })
            return
          }
          console.log(`[AUTOFILL] Extracted ${extractData.fields.length} fields:`, extractData.fields)

          // Step 3: Update store with extracted fields - use set() directly for each update
          for (const field of extractData.fields) {
            const { moduleId, questionId, value } = field
            if (moduleId && questionId && value) {
              console.log(`[AUTOFILL] Setting ${moduleId}.${questionId} = "${value.substring(0, 50)}..."`)

              // Directly update the state for each field
              set((state) => {
                const mod = state.modules[moduleId as ModuleId]
                if (!mod) {
                  console.log(`[AUTOFILL] Module ${moduleId} not found`)
                  return state
                }

                const updatedSubsections = mod.subsections.map((subsection) => ({
                  ...subsection,
                  questions: subsection.questions.map((question) =>
                    question.id === questionId
                      ? {
                        ...question,
                        value,
                        completed: true,
                      }
                      : question
                  ),
                }))

                const allQuestions = updatedSubsections.flatMap(s => s.questions).filter(q => q.type !== 'readonly')
                const completedQuestions = allQuestions.filter(q => q.completed)
                const completionPercentage = allQuestions.length > 0
                  ? Math.round((completedQuestions.length / allQuestions.length) * 100)
                  : 0

                console.log(`[AUTOFILL] Updated ${moduleId}.${questionId}, new completion: ${completionPercentage}%`)

                return {
                  modules: {
                    ...state.modules,
                    [moduleId]: {
                      ...module,
                      subsections: updatedSubsections,
                      completionPercentage,
                    },
                  },
                }
              })
            }
          }

          console.log('[AUTOFILL] Complete!')
        } catch (error) {
          console.error('[AUTOFILL] Error:', error)
        } finally {
          set({ isAutofilling: false })
        }
      },
    }),
    {
      name: "launchpad-storage-v2",
      partialize: (state: AppState) => {
        // Exclude VC state from persistence so it resets on reload/restart
        const { vcReport, vcCallCompleted, vcMessages, ...rest } = state
        return rest
      },
    }
  )
)
