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
        
        # Skip to greeting
        for _ in range(10):
            m = json.loads(await ws.recv())
            if m['type'] == 'agent_response':
                print('Got greeting, sending text...')
                break
        
        await ws.send(json.dumps({'type': 'user_turn', 'text': 'Book flight to Tokyo'}))
        
        audio_count = 0
        for _ in range(20):
            try:
                m = json.loads(await asyncio.wait_for(ws.recv(), 1.5))
                if m['type'] == 'audio':
                    audio_count += 1
                    if audio_count == 1:  # Print first audio event's structure
                        au = m.get('audio_event', {})
                        print('Audio event keys:', list(au.keys()))
                        for k in au.keys():
                            v = au[k]
                            if isinstance(v, str):
                                val_str = v[:80] if len(v) > 80 else v
                                print(f'  {k}: {val_str}')
                            else:
                                type_name = type(v).__name__
                                length = len(v) if hasattr(v, '__len__') else '?'
                                print(f'  {k}: {type_name} (length: {length})')
                elif m['type'] != 'ping':
                    print('Got', m['type'])
            except asyncio.TimeoutError:
                break
        
        print('Total audio chunks:', audio_count)

asyncio.run(test())
