#!/usr/bin/env python
"""
Debug script: Capture and display EVERY frame from ElevenLabs
Shows exact timing and content of each message type for each turn.
"""
import asyncio
import json
import sys
import os
import time
from typing import Any

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.getcwd())

import websockets
from refinement_loop.config import ELEVENLABS_AGENT_ID, ELEVENLABS_API_KEY

_WS_URL = (
    f"wss://api.elevenlabs.io/v1/convai/conversation"
    f"?agent_id={ELEVENLABS_AGENT_ID}"
)

async def main():
    extra_headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    print("=" * 80)
    print("FRAME-BY-FRAME DEBUG CAPTURE")
    print("=" * 80)
    print(f"\nConnecting to {_WS_URL}...")
    
    async with websockets.connect(_WS_URL, additional_headers=extra_headers) as ws:
        print("✅ Connected\n")
        
        # Handshake
        print(">>> Sending handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "enable_model_fallback": False,
                },
                "client_tool_result": {
                    "notification_level": "silent",
                },
            },
        }))
        
        init_resp_raw = await ws.recv()
        init_resp = json.loads(init_resp_raw)
        print(f"<<< Received handshake response (type: {init_resp.get('type')})\n")
        
        # Three customer turns
        customer_texts = [
            "Hi, I'd like to book a flight to Tokyo for next week.",
            "Economy class is fine for me.",
            "Great, can you go ahead and book that flight?",
        ]
        
        for turn_num, customer_text in enumerate(customer_texts, 1):
            print("=" * 80)
            print(f"TURN {turn_num}")
            print("=" * 80)
            
            # Send
            print(f"\n>>> Sending customer message:")
            print(f"    '{customer_text}'")
            start_time = time.time()
            await ws.send(json.dumps({
                "type": "user_turn",
                "user_turn": {"text": customer_text},
            }))
            
            # Receive frames
            frames_received = []
            frame_start = time.time()
            audio_chars = []
            last_frame_time = frame_start
            got_agent_response = False  # Track if we got the final response
            
            print(f"\n<<< Receiving frames...")
            
            while True:
                try:
                    frame_data = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    frame_time = time.time()
                    elapsed = frame_time - frame_start
                    time_since_last = frame_time - last_frame_time
                    
                    frame = json.loads(frame_data)
                    frame_type = frame.get("type", "UNKNOWN")
                    frames_received.append((elapsed, frame_type, frame))
                    last_frame_time = frame_time
                    
                    # Detailed output
                    if frame_type == "agent_response":
                        resp_text = frame.get("agent_response_event", {}).get("agent_response", "")
                        print(f"    [{elapsed:.2f}s] AGENT_RESPONSE: '{resp_text}'")
                        audio_chars.append(resp_text)
                        got_agent_response = True
                        # CRITICAL: Stop immediately after AGENT_RESPONSE
                        # This is the signal that the agent is done speaking
                        print(f"\n    [AGENT_RESPONSE received - response complete]")
                        break
                        
                    elif frame_type == "audio":
                        audio_event = frame.get("audio_event", {})
                        alignment = audio_event.get("alignment", {})
                        chars = alignment.get("chars", [])
                        char_str = "".join(chars)
                        if chars:
                            audio_chars.extend(chars)
                            print(f"    [{elapsed:.2f}s] AUDIO: chars='{char_str}'")
                        else:
                            print(f"    [{elapsed:.2f}s] AUDIO: (empty alignment)")
                            
                    elif frame_type in ("turn_started", "turn_start"):
                        print(f"    [{elapsed:.2f}s] TURN_START")
                        
                    elif frame_type == "user_turn_finished":
                        print(f"    [{elapsed:.2f}s] USER_TURN_FINISHED")
                        
                    elif frame_type == "conversation_ended":
                        print(f"    [{elapsed:.2f}s] CONVERSATION_ENDED")
                        break
                        
                    elif frame_type == "ping":
                        # Don't print every ping, they're too frequent
                        pass
                        
                    else:
                        print(f"    [{elapsed:.2f}s] {frame_type}: {str(frame)[:60]}")
                    
                    # If we have audio AND 1.5s of silence (ignoring PINGs), stop
                    if audio_chars and not got_agent_response:
                        if (time.time() - last_frame_time) > 1.5:
                            print(f"\n    [Silence detected after audio, stopping]")
                            break
                        
                except asyncio.TimeoutError:
                    print(f"    [3s timeout - no more frames]")
                    break
            
            # Summary for this turn
            total_elapsed = time.time() - frame_start
            full_response = "".join(audio_chars) if audio_chars else "(no response)"
            print(f"\nTurn {turn_num} summary:")
            print(f"  Frames received: {len(frames_received)}")
            print(f"  Total duration: {total_elapsed:.2f}s")
            print(f"  Full response: '{full_response}'")
            print()
            
            # Wait before next turn
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    asyncio.run(main())
