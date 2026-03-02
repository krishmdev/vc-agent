import { NextRequest, NextResponse } from "next/server";

import { RESEARCH_SERVICE_URL, proxyJson } from "@/lib/services";

export async function POST(req: NextRequest) {
  try {
    const { status, data } = await proxyJson(`${RESEARCH_SERVICE_URL}/chat`, await req.json());
    // Pass 4xx through (409: the first research turn for this session is still running).
    return NextResponse.json(data, { status });
  } catch (error) {
    console.error("Research Agent Proxy Error:", error);
    return NextResponse.json({ error: "Failed to communicate with research agent" }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
    const { searchParams } = new URL(req.url);
    const taskId = searchParams.get('taskId');

    if (!taskId) {
        return NextResponse.json({ error: "Missing taskId" }, { status: 400 });
    }

    try {
        const response = await fetch(`${RESEARCH_SERVICE_URL}/chat/status/${encodeURIComponent(taskId)}`);
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        // Pass the status through: a 404 means the task is gone (e.g. the agent restarted).
        return NextResponse.json(data, { status: response.status });
    } catch (error: any) {
        console.error("Polling Error:", error);
        return NextResponse.json({ error: "Failed to poll status" }, { status: 500 });
    }
}
