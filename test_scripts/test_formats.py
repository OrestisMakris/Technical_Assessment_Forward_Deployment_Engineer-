import asyncio
import websockets
import json
import os
import sys

sys.path.append(os.getcwd())
from refinement_loop.config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID

async def try_format(ws, payload):
    print(f"\n--- Trying format: {payload} ---")
    await ws.send(json.dumps(payload))
    for i in range(5):
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            data = json.loads(msg)
            t = data.get('type')
            if t == 'agent_response':
                print("SUCCESS!", data['agent_response_event']['agent_response'])
                return True
            else:
                pass
        except asyncio.TimeoutError:
            print("Timeout")
            break
    return False

async def main():
    uri = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}'
    headers = {'xi-api-key': ELEVENLABS_API_KEY}
    async with websockets.connect(uri, additional_headers=headers) as ws:
        await ws.send(json.dumps({
            'type': 'conversation_initiation_client_data',
        }))
        # flush greeting
        for _ in range(10):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0))
                if msg.get("type") == "agent_response":
                    break
            except Exception:
                pass
                
        await try_format(ws, {"text": "hi"})
        await try_format(ws, {"type": "text", "text": "hi"})
        await try_format(ws, {"type": "user_msg", "text": "hi"})
        await try_format(ws, {"type": "message", "text": "hi"})
        await try_format(ws, {"type": "user_message", "message": "hi"})
        await try_format(ws, {"type": "user", "text": "hi"})
        await try_format(ws, {"type": "user_turn", "text": "hi"})
        await try_format(ws, {"type": "user_text", "text": "hi"})
        
asyncio.run(main())