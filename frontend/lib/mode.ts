// Build-time switch. `NEXT_PUBLIC_VC_AGENT_MODE=offline` swaps every voice widget for the text
// chat panel, which talks to the voice agent's text transport instead of LiveKit.
export const OFFLINE = process.env.NEXT_PUBLIC_VC_AGENT_MODE === "offline"

export const AGENT_WS_URL = (process.env.NEXT_PUBLIC_AGENT_WS_URL || "ws://127.0.0.1:8001").replace(/\/$/, "")
