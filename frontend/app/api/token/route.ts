import { AccessToken } from "livekit-server-sdk";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const room = request.nextUrl.searchParams.get("room");
  const username = request.nextUrl.searchParams.get("username");
  const startupIdea = request.nextUrl.searchParams.get("idea");

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
    metadata: startupIdea ? JSON.stringify({ startupIdea }) : undefined,
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
