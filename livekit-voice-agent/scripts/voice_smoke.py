"""Headless live smoke test of one LiveKit voice session (needs keys, network, and a running
`agent.py dev` worker).

A scripted "founder" joins a fresh room with the same token metadata the web app sends, waits
for the agent's greeting, then plays a pre-rendered WAV question into its microphone track. It
records how much agent audio arrived and the agent's transcriptions, and prints a JSON summary.

    uv run python scripts/voice_smoke.py --wav question.wav --idea "..." [--out result.json]

The WAV must be 16-bit mono PCM (make one with `say` + `afconvert` on macOS).
"""

import argparse
import asyncio
import json
import os
import time
import sys
import wave
from pathlib import Path

from livekit import api, rtc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402  (loads .env.local in live mode)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", required=True)
    parser.add_argument("--idea", required=True)
    parser.add_argument("--mode", default="mentor")
    parser.add_argument("--listen", type=float, default=35.0, help="seconds to listen after speaking")
    parser.add_argument("--out")
    args = parser.parse_args()

    room_name = f"smoke-{int(time.time())}"
    token = (
        api.AccessToken(os.environ["LIVEKIT_API_KEY"], os.environ["LIVEKIT_API_SECRET"])
        .with_identity("smoke-founder")
        .with_metadata(json.dumps({"startupIdea": args.idea, "agentMode": args.mode}))
        .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True, can_publish_data=True))
        .to_jwt()
    )

    room = rtc.Room()
    started = time.monotonic()
    stats = {"agent_joined_s": None, "first_audio_s": None, "audio_frames": 0, "audio_seconds": 0.0}
    transcripts: list[dict] = []

    async def pump(track: rtc.Track) -> None:
        async for event in rtc.AudioStream(track):
            frame = event.frame
            # count frames with signal, not silence
            samples = frame.data  # int16 memoryview
            if any(abs(samples[i]) > 500 for i in range(0, len(samples), 40)):
                if stats["first_audio_s"] is None:
                    stats["first_audio_s"] = round(time.monotonic() - started, 2)
                stats["audio_frames"] += 1
                stats["audio_seconds"] += frame.samples_per_channel / frame.sample_rate

    @room.on("participant_connected")
    def _joined(p: rtc.RemoteParticipant):
        if stats["agent_joined_s"] is None:
            stats["agent_joined_s"] = round(time.monotonic() - started, 2)

    @room.on("track_subscribed")
    def _track(track, pub, participant):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            asyncio.ensure_future(pump(track))

    async def on_text(reader: rtc.TextStreamReader, identity: str):
        text = await reader.read_all()
        attrs = reader.info.attributes or {}
        if text.strip():
            transcripts.append({"t": round(time.monotonic() - started, 2), "from": identity, "final": attrs.get("lk.transcription_final"), "text": text})

    room.register_text_stream_handler("lk.transcription", lambda r, i: asyncio.ensure_future(on_text(r, i)))
    await room.connect(os.environ["LIVEKIT_URL"], token)

    source = rtc.AudioSource(48000, 1)
    track = rtc.LocalAudioTrack.create_audio_track("mic", source)
    await room.local_participant.publish_track(track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE))

    async def push_silence(seconds: float):
        frame = rtc.AudioFrame.create(48000, 1, 480)
        for _ in range(int(seconds * 100)):
            await source.capture_frame(frame)

    # Wait for the greeting while sending silence (keeps the track alive).
    await push_silence(12)
    greeting_audio = stats["audio_seconds"]

    with wave.open(args.wav, "rb") as wav:
        rate, pcm = wav.getframerate(), wav.readframes(wav.getnframes())
    assert rate == 48000 and len(pcm) % 2 == 0, "WAV must be 48 kHz 16-bit mono"
    spoke_at = round(time.monotonic() - started, 2)
    step = 480 * 2
    for i in range(0, len(pcm) - step, step):
        frame = rtc.AudioFrame(pcm[i : i + step], 48000, 1, 480)
        await source.capture_frame(frame)
    await push_silence(args.listen)

    await room.disconnect()
    result = {
        "room": room_name,
        "mode": args.mode,
        "voice_model": config.VOICE_MODEL,
        "agent_joined_s": stats["agent_joined_s"],
        "first_agent_audio_s": stats["first_audio_s"],
        "agent_audio_seconds_before_question": round(greeting_audio, 1),
        "agent_audio_seconds_total": round(stats["audio_seconds"], 1),
        "question_sent_at_s": spoke_at,
        "transcripts": transcripts,
    }
    text = json.dumps(result, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w") as fh:
            fh.write(text + "\n")
    return 0 if stats["audio_seconds"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
