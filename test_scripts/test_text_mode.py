import asyncio
import websockets
import json
import os
import sys

sys.path.append(os.getcwd())
from refinement_loop.config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID

async def test_text_mode():
    uri = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}'
    headers = {'xi-api-key': ELEVENLABS_API_KEY}
    
    async with websockets.connect(uri, additional_headers=headers) as ws:
        print("Sending handshake...")
        await ws.send(json.dumps({
            'type': 'conversation_initiation_client_data',
            'conversation_config_override': {}
        }))
        
        print("\n=== GREETING ===")
        for i in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                data = json.loads(msg)
                t = data.get('type')
                
                if t == 'agent_response':
                    resp_text = data['agent_response_event']['agent_response']
                    print(f"[{i}] Got agent_response: {resp_text[:50]}...")
                    break
                else:
                    print(f"[{i}] Got {t}")
            except asyncio.TimeoutError:
                print(f"[{i}] Timeout")
                break
        
        print("\n=== SENDING TEXT ===")
        # CORRECT FORMAT: user_turn as a nested object
        await ws.send(json.dumps({
            'type': 'user_turn',
            'user_turn': {'text': 'I need to book a flight to Tokyo'}
        }))
        
        print("\nWaiting for response...")
        for i in range(15):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.5)
                data = json.loads(msg)
                t = data.get('type')
                
                if t == 'agent_response':
                    resp_text = data['agent_response_event']['agent_response']
                    print(f"✅ [{i}] Got agent_response (TEXT MODE WORKS!): {resp_text[:60]}...")
                    break
                elif t == 'audio':
                    print(f"❌ [{i}] Got audio (still in audio mode)")
                elif t == 'audio_burst':
                    print(f"❌ [{i}] Got audio_burst")
                elif t != 'ping':
                    print(f"[{i}] Got {t}")
            except asyncio.TimeoutError:
                print(f"[{i}] Timeout")
                break

asyncio.run(test_text_mode())
