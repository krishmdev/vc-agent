import { NextRequest, NextResponse } from "next/server";

import { RESEARCH_SERVICE_URL } from "@/lib/services";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    // body: { message, session_id, idea, problem... }

    const response = await fetch(`${RESEARCH_SERVICE_URL}/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
        throw new Error(`Research service error: ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("Research Agent Proxy Error:", error);
    return NextResponse.json({ error: "Failed to communicate with research agent" }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
    const { searchParams } = new URL(req.url);
    const taskId = searchParams.get('taskId');
    const action = searchParams.get('action'); // 'status'

    if (!taskId) {
        return NextResponse.json({ error: "Missing taskId" }, { status: 400 });
    }

    try {
        const response = await fetch(`${RESEARCH_SERVICE_URL}/chat/status/${taskId}`);
        const data = await response.json().catch(() => ({ detail: response.statusText }));
        // Pass the status through: a 404 means the task is gone (e.g. the agent restarted).
        return NextResponse.json(data, { status: response.status });
    } catch (error: any) {
        console.error("Polling Error:", error);
        return NextResponse.json({ error: "Failed to poll status" }, { status: 500 });
    }
}
