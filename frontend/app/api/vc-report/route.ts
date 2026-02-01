
import { NextResponse } from 'next/server';

// Temporary in-memory storage for the hackathon
// In a real app, this would be a database
let storedReport: any = null;

export async function POST(req: Request) {
  try {
    const body = await req.json();
    storedReport = body;
    console.log("[API] Received VC Report:", body ? "Success" : "Empty");
    return NextResponse.json({ success: true });
  } catch (e) {
    console.error("[API] Failed to parse report:", e);
    return NextResponse.json({ success: false, error: "Invalid request" }, { status: 400 });
  }
}

// Long polling helper
const waitForReport = async (timeoutMs: number = 30000): Promise<any> => {
  const startTime = Date.now();
  while (Date.now() - startTime < timeoutMs) {
    if (storedReport) return storedReport;
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  return null;
};

export async function GET() {
  // Wait for the report if it doesn't exist yet (Long Polling)
  // This reduces client-side request spam
  if (!storedReport) {
      await waitForReport();
  }

  return NextResponse.json({ 
    report: storedReport,
    exists: !!storedReport 
  });
}
