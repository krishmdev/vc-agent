import { NextRequest, NextResponse } from "next/server"
import { RESEARCH_SERVICE_URL, proxyJson } from "@/lib/services"

export async function POST(req: NextRequest) {
  try {
    const { status, data } = await proxyJson(`${RESEARCH_SERVICE_URL}/resource_chat`, await req.json())
    return NextResponse.json(data, { status })
  } catch (error) {
    console.error("Resource chat proxy error:", error)
    return NextResponse.json({ detail: "The research agent isn't reachable." }, { status: 502 })
  }
}
