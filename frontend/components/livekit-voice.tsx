"use client";

import { useCallback, useEffect, useState } from "react";
import {
  LiveKitRoom,
  useVoiceAssistant,
  BarVisualizer,
  RoomAudioRenderer,
  VoiceAssistantControlBar,
  AgentState,
  DisconnectButton,
} from "@livekit/components-react";
import { MediaDeviceFailure } from "livekit-client";
import "@livekit/components-styles";

interface LiveKitVoiceProps {
  roomName: string;
  onConnectionChange?: (connected: boolean) => void;
  onAgentStateChange?: (state: AgentState) => void;
}

function VoiceAssistantUI({
  onAgentStateChange,
}: {
  onAgentStateChange?: (state: AgentState) => void;
}) {
  const { state, audioTrack } = useVoiceAssistant();

  useEffect(() => {
    onAgentStateChange?.(state);
  }, [state, onAgentStateChange]);

  return (
    <div className="flex flex-col items-center gap-4">
      <BarVisualizer
        state={state}
        barCount={5}
        trackRef={audioTrack}
        className="w-48 h-48"
        options={{ minHeight: 24 }}
      />
      <p className="text-sm text-muted-foreground capitalize">
        {state === "listening"
          ? "Listening..."
          : state === "thinking"
          ? "Thinking..."
          : state === "speaking"
          ? "Speaking..."
          : "Connecting..."}
      </p>
      <VoiceAssistantControlBar controls={{ leave: false }} />
    </div>
  );
}

export function LiveKitVoice({
  roomName,
  onConnectionChange,
  onAgentStateChange,
}: LiveKitVoiceProps) {
  const [token, setToken] = useState<string | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchToken() {
      try {
        const response = await fetch(
          `/api/token?room=${encodeURIComponent(roomName)}`
        );
        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || "Failed to get token");
        }

        setToken(data.token);
        setUrl(data.url);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to connect");
      }
    }

    fetchToken();
  }, [roomName]);

  const handleDeviceError = useCallback((failure?: MediaDeviceFailure) => {
    console.error("Device error:", failure);
    setError(`Microphone error: ${failure?.toString() || "Unknown error"}`);
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-4 p-8">
        <p className="text-destructive text-sm">{error}</p>
        <button
          onClick={() => {
            setError(null);
            setToken(null);
          }}
          className="text-sm underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (!token || !url) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-pulse text-muted-foreground">Connecting...</div>
      </div>
    );
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={url}
      connect={true}
      audio={true}
      video={false}
      onMediaDeviceFailure={handleDeviceError}
      onConnected={() => onConnectionChange?.(true)}
      onDisconnected={() => onConnectionChange?.(false)}
      className="flex flex-col items-center"
    >
      <VoiceAssistantUI onAgentStateChange={onAgentStateChange} />
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

export function LiveKitVoiceSimple({
  roomName,
  onEnd,
}: {
  roomName: string;
  onEnd?: () => void;
}) {
  const [token, setToken] = useState<string | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    async function fetchToken() {
      const response = await fetch(
        `/api/token?room=${encodeURIComponent(roomName)}`
      );
      const data = await response.json();
      setToken(data.token);
      setUrl(data.url);
    }
    fetchToken();
  }, [roomName]);

  if (!token || !url) {
    return <div className="animate-pulse">Connecting...</div>;
  }

  return (
    <LiveKitRoom
      token={token}
      serverUrl={url}
      connect={true}
      audio={true}
      video={false}
      onConnected={() => setConnected(true)}
      onDisconnected={() => {
        setConnected(false);
        onEnd?.();
      }}
    >
      <SimpleVoiceUI connected={connected} />
      <RoomAudioRenderer />
    </LiveKitRoom>
  );
}

function SimpleVoiceUI({ connected }: { connected: boolean }) {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <div className="flex flex-col items-center gap-6">
      <BarVisualizer
        state={state}
        barCount={7}
        trackRef={audioTrack}
        className="w-64 h-64"
      />
      <div className="flex flex-col items-center gap-2">
        <span className="text-lg font-medium capitalize">
          {state === "listening"
            ? "Listening to you..."
            : state === "thinking"
            ? "Thinking..."
            : state === "speaking"
            ? "Mentor is speaking..."
            : connected
            ? "Connected"
            : "Connecting..."}
        </span>
      </div>
      <DisconnectButton className="px-4 py-2 bg-destructive text-destructive-foreground rounded-full">
        End Call
      </DisconnectButton>
    </div>
  );
}
