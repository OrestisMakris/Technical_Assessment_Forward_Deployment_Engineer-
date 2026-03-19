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
                break
        
        await ws.send(json.dumps({'type': 'client_event', 'client_event': { 'type': 'user_turn', 'text': 'Hello there!'}}))
        print('Sent client_event format, waiting...')
        for _ in range(5):
            msg = json.loads(await asyncio.wait_for(ws.recv(), 5.0))
            if msg.get('type') not in ['ping']:
                print("Received frame:", msg)
                
asyncio.run(check())
