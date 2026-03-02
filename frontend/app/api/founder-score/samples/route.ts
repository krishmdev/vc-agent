import { NextResponse } from "next/server"
import { RESEARCH_SERVICE_URL } from "@/lib/services"

export const dynamic = "force-dynamic"

export async function GET() {
  try {
    const response = await fetch(`${RESEARCH_SERVICE_URL}/founder/samples`)
    return NextResponse.json(await response.json(), { status: response.status })
  } catch (error) {
    console.error("Founder samples proxy error:", error)
    return NextResponse.json({ detail: "The research agent isn't reachable." }, { status: 502 })
  }
}
