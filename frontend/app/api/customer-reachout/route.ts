import { NextRequest, NextResponse } from "next/server";

const RESEARCH_SERVICE_URL = "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    // body: { icp_description, customer_type }

    const response = await fetch(`${RESEARCH_SERVICE_URL}/customer-reachout`, {
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
    console.error("Customer Reachout Proxy Error:", error);
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
        const response = await fetch(`${RESEARCH_SERVICE_URL}/chat/status/${taskId}`);
        if (!response.ok) {
             throw new Error(`Service error: ${response.statusText}`);
        }
        const data = await response.json();
        
        // Parse content if it's a string (which it is from the backend)
        if (data.status === 'completed' && data.content && typeof data.content === 'string') {
            try {
                data.content = JSON.parse(data.content);
            } catch (e) {
                console.error("Failed to parse content JSON", e);
            }
        }
        
        return NextResponse.json(data);
    } catch (error: any) {
        console.error("Polling Error:", error);
        return NextResponse.json({ error: "Failed to poll status" }, { status: 500 });
    }
}
