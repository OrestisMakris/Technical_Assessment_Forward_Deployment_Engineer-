import asyncio
import json
import os
import sys

import websockets

sys.path.append(os.getcwd())
from refinement_loop.config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID

URI = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"
HEADERS = {"xi-api-key": ELEVENLABS_API_KEY}


async def recv_until_pause(ws, timeout=1.2, max_frames=120):
    frames = []
    for _ in range(max_frames):
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            break
        msg = json.loads(raw)
        frames.append(msg)
    return frames


def summarize(frames):
    kinds = {}
    texts = []
    for m in frames:
        t = m.get("type", "")
        kinds[t] = kinds.get(t, 0) + 1
        if t == "agent_response":
            txt = m.get("agent_response_event", {}).get("agent_response", "")
            if txt:
                texts.append(txt)
        elif t == "audio":
            chars = m.get("audio_event", {}).get("alignment", {}).get("chars", [])
            if chars:
                texts.append("".join(chars))
    return kinds, "".join(texts).strip()


async def run_case(case_name, user_payload):
    print("\n" + "=" * 80)
    print(case_name)
    print("=" * 80)

    async with websockets.connect(URI, additional_headers=HEADERS) as ws:
        await ws.send(json.dumps({"type": "conversation_initiation_client_data"}))

        # Consume initial server activity (greeting and setup)
        initial = await recv_until_pause(ws, timeout=1.0, max_frames=100)
        kinds, txt = summarize(initial)
        print("Initial frames:", kinds)
        if txt:
            print("Initial text:", repr(txt[:180]))

        # Send first user message in selected protocol
        await ws.send(json.dumps(user_payload))
        after = await recv_until_pause(ws, timeout=1.2, max_frames=120)
        kinds2, txt2 = summarize(after)
        print("After user msg frames:", kinds2)
        if txt2:
            print("After user msg text:", repr(txt2[:240]))
        else:
            print("After user msg text: <EMPTY>")


async def main():
    await run_case(
        "CASE A: type=user_turn",
        {"type": "user_turn", "user_turn": {"text": "I need a flight to Tokyo next Friday"}},
    )

    await run_case(
        "CASE B: type=client_event user_message",
        {
            "type": "client_event",
            "client_event": {
                "type": "user_message",
                "text": "I need a flight to Tokyo next Friday",
            },
        },
    )


if __name__ == "__main__":
    asyncio.run(main())
