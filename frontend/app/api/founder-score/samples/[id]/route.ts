import { NextRequest, NextResponse } from "next/server"
import { RESEARCH_SERVICE_URL } from "@/lib/services"

export const dynamic = "force-dynamic"

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  try {
    const response = await fetch(`${RESEARCH_SERVICE_URL}/founder/samples/${encodeURIComponent(id)}/score`)
    return NextResponse.json(await response.json(), { status: response.status })
  } catch (error) {
    console.error("Founder sample score proxy error:", error)
    return NextResponse.json({ detail: "The research agent isn't reachable." }, { status: 502 })
  }
}
