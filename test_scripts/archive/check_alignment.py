import asyncio
import websockets
import json
import os
import sys

sys.path.append(os.getcwd())
from refinement_loop.config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID

async def test():
    uri = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}'
    headers = {'xi-api-key': ELEVENLABS_API_KEY}
    
    async with websockets.connect(uri, additional_headers=headers) as ws:
        await ws.send(json.dumps({'type': 'conversation_initiation_client_data'}))
        
        for _ in range(10):
            m = json.loads(await ws.recv())
            if m['type'] == 'agent_response':
                break
        
        await ws.send(json.dumps({'type': 'user_turn', 'text': 'Book flight to Tokyo'}))
        
        for _ in range(20):
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), 1.5))
                if m['type'] == 'audio':
                    au = m.get('audio_event', {})
                    alignment = au.get('alignment', {})
                    print('=' * 60)
                    print('alignment object:', alignment)
                    print('alignment keys:', list(alignment.keys()))
                    for k, v in alignment.items():
                        print(f'  {k}: {v}')
                    break
            except asyncio.TimeoutError:
                break

asyncio.run(test())
