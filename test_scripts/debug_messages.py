#!/usr/bin/env python
"""Debug: show exactly what messages are being sent to ElevenLabs"""
import asyncio
import json
import websockets
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.getcwd())
from refinement_loop.config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID

async def debug_messages():
    uri = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}'
    headers = {'xi-api-key': ELEVENLABS_API_KEY}
    
    async with websockets.connect(uri, additional_headers=headers) as ws:
        # 1. Handshake
        print("1. Sending handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {}
        }))
        
        # Get init response
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        print(f"   Got init response")
        
        # 2. First customer turn
        print("\n2. Sending FIRST customer message...")
        msg1 = {"type": "user_turn", "user_turn": {"text": "Hi, I want to book a flight"}}
        print(f"   Message: {json.dumps(msg1)}")
        await ws.send(json.dumps(msg1))
        
        # Wait for agent response
        print("   Waiting for agent response...")
        for i in range(30):
            msg = await asyncio.wait_for(ws.recv(), timeout=1)
            data = json.loads(msg)
            if data.get('type') == 'agent_response':
                resp = data.get('agent_response_event', {}).get('agent_response', '')
                print(f"   Got agent_response: {resp[:60]}...")
                break
            elif data.get('type') == 'ping':
                pass  # ignore pings
        
        # 3. Second customer turn
        print("\n3. Sending SECOND customer message...")
        msg2 = {"type": "user_turn", "user_turn": {"text": "Next Friday works for me"}}
        print(f"   Message: {json.dumps(msg2)}")
        await ws.send(json.dumps(msg2))
        
        # Wait for agent response
        print("   Waiting for agent response...")
        got_response = False
        for i in range(30):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1)
                data = json.loads(msg)
                if data.get('type') == 'agent_response':
                    resp = data.get('agent_response_event', {}).get('agent_response', '')
                    print(f"   Got agent_response: {resp[:60]}...")
                    got_response = True
                    break
                elif data.get('type') == 'ping':
                    pass
                else:
                    print(f"   Got {data.get('type')}")
            except asyncio.TimeoutError:
                print(f"   [{i}] Timeout waiting for response")
        
        if not got_response:
            print("   ERROR: No agent_response received!")
        
        print("\n4. Closing...")
        await ws.send(json.dumps({"type": "end_conversation"}))

print("ElevenLabs Multi-turn Message Debug")
print("=" * 60)
asyncio.run(debug_messages())
