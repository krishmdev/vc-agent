import { test as base, expect } from "@playwright/test"

const LOCAL = new Set(["127.0.0.1", "localhost"])

// Browser-side egress block: anything that isn't localhost is aborted and recorded.
export const test = base.extend<{ blockedRequests: string[] }>({
  blockedRequests: async ({ context }, use) => {
    const blocked: string[] = []
    await context.route("**/*", (route) => {
      const url = new URL(route.request().url())
      if (url.protocol === "data:" || url.protocol === "blob:" || LOCAL.has(url.hostname)) return route.continue()
      blocked.push(url.href)
      return route.abort()
    })
    await use(blocked)
  },
})

export { expect }

export const SAMPLE_IDEA =
  "Practice-management software for independent veterinary clinics that automates appointment reminders, inventory reordering, and pet-insurance claims."
