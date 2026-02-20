// Server-side base URLs for the two Python services.
export const RESEARCH_SERVICE_URL = (process.env.RESEARCH_SERVICE_URL || "http://127.0.0.1:8000").replace(/\/$/, "")
export const AGENT_SERVICE_URL = (process.env.AGENT_SERVICE_URL || "http://127.0.0.1:8001").replace(/\/$/, "")

// Runtime gate for server routes. Checks both the runtime env and the build-time public flag,
// so an offline build can't be flipped live by env files and a live build run with
// VC_AGENT_MODE=offline also stays offline. Routes that would use a provider key fail closed.
export function isOffline() {
  return process.env.VC_AGENT_MODE === "offline" || process.env.NEXT_PUBLIC_VC_AGENT_MODE === "offline"
}

export async function proxyJson(url: string, body: unknown) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const data = await response.json().catch(() => ({ detail: `${response.status} ${response.statusText}` }))
  return { status: response.status, data }
}
