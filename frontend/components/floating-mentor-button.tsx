"use client";

import { useCallback, useEffect, useState } from "react";
import {
    LiveKitRoom,
    useVoiceAssistant,
    BarVisualizer,
    RoomAudioRenderer,
    DisconnectButton,
} from "@livekit/components-react";
import { MediaDeviceFailure } from "livekit-client";
import "@livekit/components-styles";
import { Phone, PhoneOff, X, Headphones } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";

interface FloatingMentorButtonProps {
    className?: string;
}

function ActiveCallUI({ onEnd }: { onEnd: () => void }) {
    const { state, audioTrack } = useVoiceAssistant();

    return (
        <div className="flex flex-col items-center gap-4 p-4">
            {/* Voice Visualizer */}
            <div className="relative">
                <BarVisualizer
                    state={state}
                    barCount={5}
                    trackRef={audioTrack}
                    className="w-32 h-32"
                    options={{ minHeight: 16 }}
                />
            </div>

            {/* Status Text */}
            <p className="text-sm font-medium text-foreground capitalize">
                {state === "listening"
                    ? "Listening..."
                    : state === "thinking"
                        ? "Thinking..."
                        : state === "speaking"
                            ? "Mentor speaking..."
                            : "Connecting..."}
            </p>

            {/* End Call Button */}
            <DisconnectButton
                onClick={onEnd}
                className="flex items-center gap-2 px-4 py-2 bg-destructive text-destructive-foreground rounded-full text-sm font-medium hover:bg-destructive/90 transition-colors"
            >
                <PhoneOff className="w-4 h-4" />
                End Call
            </DisconnectButton>
        </div>
    );
}

export function FloatingMentorButton({ className }: FloatingMentorButtonProps) {
    const { idea } = useAppStore();
    const [isOpen, setIsOpen] = useState(false);
    const [isConnecting, setIsConnecting] = useState(false);
    const [token, setToken] = useState<string | null>(null);
    const [url, setUrl] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Generate a unique room name for this call
    const roomName = `mentor-quickcall-${Date.now()}`;

    const handleConnect = async () => {
        setIsConnecting(true);
        setError(null);

        try {
            const params = new URLSearchParams({
                room: roomName,
            });
            if (idea) {
                params.set("idea", idea);
            }

            const response = await fetch(`/api/token?${params.toString()}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || "Failed to get token");
            }

            setToken(data.token);
            setUrl(data.url);
            setIsOpen(true);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to connect");
        } finally {
            setIsConnecting(false);
        }
    };

    const handleDisconnect = useCallback(() => {
        setIsOpen(false);
        setToken(null);
        setUrl(null);
        setError(null);
    }, []);

    const handleDeviceError = useCallback((failure?: MediaDeviceFailure) => {
        console.error("Device error:", failure);
        setError(`Microphone error: ${failure?.toString() || "Unknown error"}`);
    }, []);

    // If expanded and connected, show the call UI
    if (isOpen && token && url) {
        return (
            <div
                className={cn(
                    "fixed bottom-6 left-6 z-50",
                    "w-64 bg-card border border-border rounded-2xl shadow-2xl",
                    "animate-in slide-in-from-bottom-4 fade-in duration-300",
                    className
                )}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-3 border-b border-border">
                    <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                        <span className="text-sm font-medium text-foreground">Mentor Call</span>
                    </div>
                    <button
                        onClick={handleDisconnect}
                        className="p-1 rounded-full hover:bg-secondary transition-colors"
                        aria-label="Close"
                    >
                        <X className="w-4 h-4 text-muted-foreground" />
                    </button>
                </div>

                {/* LiveKit Room */}
                <LiveKitRoom
                    token={token}
                    serverUrl={url}
                    connect={true}
                    audio={true}
                    video={false}
                    onMediaDeviceFailure={handleDeviceError}
                    onDisconnected={handleDisconnect}
                >
                    <ActiveCallUI onEnd={handleDisconnect} />
                    <RoomAudioRenderer />
                </LiveKitRoom>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div
                className={cn(
                    "fixed bottom-6 left-6 z-50",
                    "w-64 p-4 bg-card border border-destructive/50 rounded-2xl shadow-2xl",
                    className
                )}
            >
                <p className="text-sm text-destructive mb-3">{error}</p>
                <button
                    onClick={() => setError(null)}
                    className="text-sm underline text-muted-foreground hover:text-foreground"
                >
                    Dismiss
                </button>
            </div>
        );
    }

    // Idle state - floating button
    return (
        <button
            onClick={handleConnect}
            disabled={isConnecting}
            className={cn(
                "fixed bottom-6 left-6 z-50",
                "w-14 h-14 rounded-full",
                "bg-primary text-primary-foreground",
                "shadow-lg shadow-primary/25",
                "flex items-center justify-center",
                "hover:scale-110 hover:shadow-xl hover:shadow-primary/30",
                "active:scale-95",
                "transition-all duration-200 ease-out",
                "group",
                isConnecting && "animate-pulse",
                className
            )}
            aria-label="Call mentor"
        >
            {isConnecting ? (
                <div className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
            ) : (
                <>
                    <Headphones className="w-6 h-6 group-hover:scale-110 transition-transform" />
                </>
            )}
        </button>
    );
}
