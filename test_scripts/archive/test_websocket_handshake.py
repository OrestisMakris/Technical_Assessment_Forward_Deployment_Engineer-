"""
Test the exact WebSocket handshake sequence to see where agent greeting should appear.
"""

import asyncio
import json
from dotenv import load_dotenv
import os

try:
    import websockets
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "websockets"])
    import websockets

load_dotenv()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

async def test_handshake():
    print("=" * 80)
    print("🔍 TESTING WEBSOCKET HANDSHAKE SEQUENCE")
    print("=" * 80)
    
    uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
    
    async with websockets.connect(uri, additional_headers={"xi-api-key": API_KEY}) as ws:
        print(f"\n✅ Connected\n")
        
        # Step 1: Send handshake
        print("📤 STEP 1: Sending conversation_initiation_client_data")
        handshake = {
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "enable_model_fallback": False,
                },
                "client_tool_result": {
                    "notification_level": "silent",
                },
            },
        }
        await ws.send(json.dumps(handshake))
        print(f"   Sent: {json.dumps(handshake, indent=2)}")
        
        # Step 2: Listen for responses
        print(f"\n📥 STEP 2: Listening for server responses (60 second timeout)\n")
        
        timeout = 60
        start_time = asyncio.get_running_loop().time()
        message_num = 0
        
        try:
            while True:
                remaining = timeout - (asyncio.get_running_loop().time() - start_time)
                if remaining <= 0:
                    print(f"\n⏱️  Timeout after {timeout} seconds")
                    break
                
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
                message_num += 1
                
                try:
                    msg = json.loads(msg_raw)
                    msg_type = msg.get('type', 'unknown')
                    
                    print(f"Message #{message_num} ({msg_type}):")
                    
                    if msg_type == 'conversation_initiation_metadata':
                        meta = msg.get('conversation_initiation_metadata_event', {})
                        conv_id = meta.get('conversation_id', 'unknown')
                        print(f"  ✅ Handshake complete - Conversation ID: {conv_id}")
                    
                    elif msg_type == 'agent_response':
                        agent_text = msg.get('agent_response_event', {}).get('agent_response', '')
                        print(f"  🤖 Agent: {agent_text}")
                    
                    elif msg_type == 'audio':
                        audio_event = msg.get('audio_event', {})
                        alignment = audio_event.get('alignment', {})
                        chars = alignment.get('chars', [])
                        if chars:
                            print(f"  🔊 Audio chars: {''.join(chars)}")
                    
                    elif msg_type in ['ping', 'turn_started', 'turn_start', 'user_turn_finished']:
                        print(f"  ⚙️  Control frame: {msg_type}")
                    
                    else:
                        print(f"  Full message: {json.dumps(msg, indent=2)[:300]}")
                
                except json.JSONDecodeError as e:
                    print(f"  ⚠️  Not JSON: {msg_raw[:100]}")
        
        except asyncio.TimeoutError:
            print(f"\n⏱️  No more messages (timeout)")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_handshake())
