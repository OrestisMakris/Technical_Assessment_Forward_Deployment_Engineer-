import asyncio
import websockets
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def test():
    uri = "wss://api.elevenlabs.io/v1/convai/conversation?agent_id=agent_5401km1rxwwrfjtbw7ek6kp2yqrf"
    headers = {"xi-api-key": "fake_key_is_not_read_I_will_use_the_config_one"}
    
    # Let's try different formats
    import os
    sys.path.append(os.getcwd())
    from refinement_loop.config import ELEVENLABS_API_KEY
    headers["xi-api-key"] = ELEVENLABS_API_KEY
    
    async with websockets.connect(uri, additional_headers=headers) as ws:
        await ws.send(json.dumps({"type": "conversation_initiation_client_data"}))
        print("Sent handshake")
        
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            if data["type"] == "agent_response":
                print(f"Agent: {data.get('agent_response_event', {}).get('agent_response')}")
                
                # Format 1: what we had
                msg1 = {"type": "user_turn", "text": "I want to fly to Tokyo"}
                
                # Format 2: what some examples show
                # Wait, isn't it {"user_audio_chunk": "..."} for voice?
                
                print("Sending string...")
                await ws.send(json.dumps({"type": "client_event", "client_event": {"type": "user_message", "text": "I want to fly to Tokyo"}}))
                
                # Or maybe user_audio_chunk but empty with text?
                print("Sending user_turn...")
                # await ws.send(json.dumps({"type": "user_turn" , "user_turn": {"text": "I want to fly to Tokyo."}}))
                break

asyncio.run(test())
