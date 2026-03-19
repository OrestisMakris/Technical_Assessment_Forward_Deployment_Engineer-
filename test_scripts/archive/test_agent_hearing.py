#!/usr/bin/env python
"""
Test: What do WE capture vs what does the AGENT actually respond to?

The issue is likely:
- We SEND Turn 2+, but agent doesn't actually HEAR it
- So we get silence (timeout) or incomplete responses
- ElevenLabs dashboard only records what agent heard/responded to
"""
import asyncio
import json
import sys
import os
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.getcwd())

import websockets
from refinement_loop.config import ELEVENLABS_AGENT_ID, ELEVENLABS_API_KEY

_WS_URL = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"

async def test_agent_hearing():
    """Test if agent actually hears Turn 2+"""
    extra_headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    print("=" * 80)
    print("TEST: Does agent hear Turn 2+?")
    print("=" * 80)
    
    async with websockets.connect(_WS_URL, additional_headers=extra_headers) as ws:
        # Handshake
        print("\n1. Handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {"enable_model_fallback": False},
                "client_tool_result": {"notification_level": "silent"},
            },
        }))
        init = json.loads(await ws.recv())
        print("   ✅ Connected\n")
        
        # Turn 1: Send and collect response
        print("2. TURN 1: Send 'Hi, I want to book a flight to Tokyo'")
        await ws.send(json.dumps({
            "type": "user_turn",
            "user_turn": {"text": "Hi, I want to book a flight to Tokyo"},
        }))
        
        turn1_response = []
        start_t1 = time.time()
        
        while True:
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                mtype = msg.get("type")
                
                if mtype == "agent_response":
                    resp = msg.get("agent_response_event", {}).get("agent_response", "")
                    turn1_response.append(resp)
                    elapsed = time.time() - start_t1
                    print(f"   [{elapsed:.1f}s] Agent response: '{resp}'")
                    break
                elif mtype == "audio":
                    chars = msg.get("audio_event", {}).get("alignment", {}).get("chars", [])
                    if chars:
                        turn1_response.extend(chars)
                elif mtype == "ping":
                    pass  # Ignore
                    
            except asyncio.TimeoutError:
                break
        
        if turn1_response:
            print(f"   ✅ Turn 1: Agent heard and responded\n")
        else:
            print(f"   ❌ Turn 1: No response!\n")
            return
        
        # Turn 2: Send and try to collect response
        print("3. TURN 2: Send 'Economy class is fine'")
        await ws.send(json.dumps({
            "type": "user_turn",
            "user_turn": {"text": "Economy class is fine"},
        }))
        
        turn2_response = []
        turn2_heard_agent = False
        start_t2 = time.time()
        frame_count = 0
        
        while frame_count < 50:  # Limit to 50 frames
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
                mtype = msg.get("type")
                frame_count += 1
                elapsed = time.time() - start_t2
                
                if mtype == "agent_response":
                    # If we get THIS on turn 2, it means agent heard us
                    resp = msg.get("agent_response_event", {}).get("agent_response", "")
                    turn2_response.append(resp)
                    turn2_heard_agent = True
                    print(f"   [{elapsed:.1f}s] Agent response: '{resp}'")
                    
                elif mtype == "audio":
                    chars = msg.get("audio_event", {}).get("alignment", {}).get("chars", [])
                    if chars:
                        turn2_response.extend(chars)
                        # First audio frame means agent is responding
                        if not turn2_heard_agent:
                            turn2_heard_agent = True
                            print(f"   [{elapsed:.1f}s] Audio started (agent is responding)")
                            
                elif mtype == "ping":
                    pass  # Ignore
                    
                elif mtype in ("turn_started", "user_turn_finished"):
                    print(f"   [{elapsed:.1f}s] {mtype}")
                    
            except asyncio.TimeoutError:
                elapsed = time.time() - start_t2
                if turn2_heard_agent:
                    print(f"   [{elapsed:.1f}s] No more frames")
                    break
                else:
                    print(f"   [{elapsed:.1f}s] Timeout (no response yet)")
                    break
        
        # Result
        full_resp = "".join(turn2_response) if turn2_response else "(empty)"
        if turn2_heard_agent:
            print(f"   ✅ Turn 2: Agent heard and responded: '{full_resp[:60]}'")
        else:
            print(f"   ❌ Turn 2: Agent did NOT respond (silence/timeout)")
            print(f"             Status: {full_resp}")

if __name__ == "__main__":
    asyncio.run(test_agent_hearing())
