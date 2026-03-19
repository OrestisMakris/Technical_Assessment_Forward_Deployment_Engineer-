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
        
        await ws.send(json.dumps({'type': 'user_turn', 'user_turn': {'text': 'Hello there!'}}))
        print('Sent user_turn format, waiting...')
        for _ in range(15):
            msg = json.loads(await asyncio.wait_for(ws.recv(), 15.0))
            t = msg.get('type')
            if t not in ['ping', 'agent_chat_response_part']:
                print("Received frame type:", t)
            if t == 'agent_response':
                print('Got text response:', msg['agent_response_event']['agent_response'])
                break
                
asyncio.run(check())
