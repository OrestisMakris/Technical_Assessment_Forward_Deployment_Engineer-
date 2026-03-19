import asyncio, websockets, json, os, sys
sys.path.append(os.getcwd())
from refinement_loop.config import ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID

async def check():
    uri = f'wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}'
    headers = {'xi-api-key': ELEVENLABS_API_KEY}
    async with websockets.connect(uri, additional_headers=headers) as ws:
        await ws.send(json.dumps({'type': 'conversation_initiation_client_data'}))
        for _ in range(10):
            msg = json.loads(await ws.recv())
            if msg.get('type') == 'agent_response':
                print('Got greeting:', msg['agent_response_event']['agent_response'])
                break
        
        await ws.send(json.dumps({'type': 'user_turn', 'text': 'Hello text mode'}))
        for _ in range(5):
            try:
                msg = json.loads(await asyncio.wait_for(ws.recv(), 5.0))
                if msg.get('type') == 'agent_response':
                    print('Got response:', msg['agent_response_event']['agent_response'])
                    break
            except Exception as e:
                print('Error:', e)

asyncio.run(check())
