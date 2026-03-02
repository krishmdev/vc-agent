import { NextRequest, NextResponse } from "next/server"
import { RESEARCH_SERVICE_URL, proxyJson } from "@/lib/services"

// Founder scorecard for a submitted profile. No keys here: the research agent picks the classifier.
export async function POST(req: NextRequest) {
  try {
    const { status, data } = await proxyJson(`${RESEARCH_SERVICE_URL}/founder/score`, await req.json())
    return NextResponse.json(data, { status })
  } catch (error) {
    console.error("Founder score proxy error:", error)
    return NextResponse.json({ detail: "The research agent isn't reachable." }, { status: 502 })
  }
}
