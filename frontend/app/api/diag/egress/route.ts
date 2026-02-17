import net from "node:net"
import { NextResponse } from "next/server"

// Egress canary for the Next.js server runtime. Only served when VC_AGENT_DIAGNOSTICS=1.
export const runtime = "nodejs"
export const dynamic = "force-dynamic"

const TARGETS: [string, number][] = [
  ["1.1.1.1", 443],
  ["api.openai.com", 443],
  ["generativelanguage.googleapis.com", 443],
  ["huggingface.co", 443],
]

function probe(host: string, port: number, timeoutMs = 3000) {
  return new Promise<{ target: string; connected: boolean; error?: string }>((resolve) => {
    const target = `${host}:${port}`
    const socket = net.connect({ host, port })
    const done = (connected: boolean, error?: string) => {
      socket.destroy()
      resolve({ target, connected, ...(error ? { error } : {}) })
    }
    socket.setTimeout(timeoutMs, () => done(false, "timeout"))
    socket.once("connect", () => done(true))
    socket.once("error", (err: NodeJS.ErrnoException) => done(false, `${err.code ?? "error"}: ${err.message}`.slice(0, 160)))
  })
}

export async function GET() {
  if (process.env.VC_AGENT_DIAGNOSTICS !== "1") {
    return NextResponse.json({ error: "not found" }, { status: 404 })
  }
  const results = []
  for (const [host, port] of TARGETS) results.push(await probe(host, port))
  return NextResponse.json({
    process: "nextjs-server",
    pid: process.pid,
    blocked: results.every((r) => !r.connected),
    results,
  })
}
