import { AccessToken } from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";
import { isOffline } from "@/lib/services";

export async function GET(request: NextRequest) {
  if (isOffline()) {
    return NextResponse.json({ error: "Voice calls are off in offline mode; use the text chat." }, { status: 409 });
  }
  const room = request.nextUrl.searchParams.get("room");
  const username = request.nextUrl.searchParams.get("username");
  const startupIdea = request.nextUrl.searchParams.get("idea");
  const mode = request.nextUrl.searchParams.get("mode") || "mentor"; // Default to "mentor"

  if (!room) {
    return NextResponse.json(
      { error: 'Missing "room" query parameter' },
      { status: 400 }
    );
  }

  const apiKey = process.env.LIVEKIT_API_KEY;
  const apiSecret = process.env.LIVEKIT_API_SECRET;
  const wsUrl = process.env.LIVEKIT_URL;

  if (!apiKey || !apiSecret || !wsUrl) {
    return NextResponse.json(
      { error: "Server misconfigured - missing LiveKit credentials" },
      { status: 500 }
    );
  }

  const at = new AccessToken(apiKey, apiSecret, {
    identity: username || `user-${Math.random().toString(36).substring(7)}`,
    ttl: "10m",
    metadata: JSON.stringify({
      startupIdea: startupIdea || "",
      agentMode: mode
    }),
  });

  at.addGrant({
    room,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  });

  const token = await at.toJwt();

  return NextResponse.json({
    token,
    url: wsUrl,
  });
}
