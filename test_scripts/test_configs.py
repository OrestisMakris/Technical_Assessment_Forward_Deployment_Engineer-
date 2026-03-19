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
    
    # Try different configurations
    configs = [
        {"agent": {"generate_timestamps": False}, "tts": {"enabled": False}},
        {"tts": {"enabled": False}},
        {"output_format": None},
        {"audio": {"enabled": False}},
        {"agent_output_audio_format": None},
    ]
    
    for config in configs:
        print(f"\n=== Testing config: {config} ===")
        try:
            async with websockets.connect(uri, additional_headers=headers) as ws:
                await ws.send(json.dumps({
                    'type': 'conversation_initiation_client_data',
                    'conversation_config_override': config
                }))
                
                got_greeting = False
                for i in range(10):
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(msg)
                        t = data.get('type')
                        
                        if t == 'agent_response' and not got_greeting:
                            got_greeting = True
                            print(f"  ✅ Got greeting via agent_response")
                            break
                        elif t == 'audio':
                            print(f"  ❌ Still getting audio")
                            break
                    except asyncio.TimeoutError:
                        break
                
                if not got_greeting:
                    print(f"  ❌ Didn't get agent_response greeting")
        except Exception as e:
            print(f"  Error: {e}")

asyncio.run(test_text_mode())
