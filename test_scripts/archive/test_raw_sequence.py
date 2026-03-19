"""
Simple WebSocket test - just connect, handshake, and see EXACTLY what the agent sends.
Don't consume or drain anything - just collect the raw sequence.
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

async def test():
    print("=" * 80)
    print("🔍 RAW WEBSOCKET SEQUENCE (NO DRAINING)")
    print("=" * 80)
    print("")
    
    uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
    
    async with websockets.connect(uri, additional_headers={"xi-api-key": API_KEY}) as ws:
        print("✅ Connected\n")
        
        # Send handshake
        print("📤 Sending handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {"enable_model_fallback": False},
                "client_tool_result": {"notification_level": "silent"},
            },
        }))
        
        print("📥 Listening for ALL messages (30 seconds):\n")
        
        msg_count = 0
        start = asyncio.get_running_loop().time()
        message_types = {}
        
        try:
            while asyncio.get_running_loop().time() - start < 30:
                try:
                    msg_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    msg_count += 1
                    
                    try:
                        msg = json.loads(msg_raw)
                        msg_type = msg.get('type', 'unknown')
                        message_types[msg_type] = message_types.get(msg_type, 0) + 1
                        
                        # Print key messages
                        if msg_type == 'conversation_initiation_metadata':
                            conv_id = msg.get('conversation_initiation_metadata_event', {}).get('conversation_id', '')
                            print(f"  Message #{msg_count}: {msg_type} (conv_id: {conv_id[:20]}...)")
                        elif msg_type == 'agent_response':
                            text = msg.get('agent_response_event', {}).get('agent_response', '')
                            print(f"  Message #{msg_count}: {msg_type} ✅ GREETING: '{text}'")
                        elif msg_type == 'audio':
                            chars = msg.get('audio_event', {}).get('alignment', {}).get('chars', [])
                            char_str = ''.join(chars) if chars else ''
                            if char_str.strip():
                                print(f"  Message #{msg_count}: {msg_type} (audio chars: '{char_str}')")
                            else:
                                print(f"  Message #{msg_count}: {msg_type} (ping/empty)")
                        elif msg_type == 'ping':
                            print(f"  Message #{msg_count}: {msg_type}")
                        else:
                            print(f"  Message #{msg_count}: {msg_type}")
                    
                    except json.JSONDecodeError:
                        print(f"  Message #{msg_count}: [NOT JSON] {msg_raw[:50]}")
                
                except asyncio.TimeoutError:
                    pass
        
        except KeyboardInterrupt:
            pass
        
        print(f"\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total messages: {msg_count}")
        print(f"\nMessage type breakdown:")
        for msg_type, count in sorted(message_types.items(), key=lambda x: -x[1]):
            print(f"  {msg_type}: {count}")
        
        # Key question
        if 'agent_response' in message_types:
            print(f"\n✅ AGENT SENDS INITIAL GREETING (agent_response event)")
        elif 'audio' in message_types:
            print(f"\n⚠️  Agent sends AUDIO frames only (might contain greeting in alignment chars)")
        else:
            print(f"\n❌ NO GREETING DETECTED")

if __name__ == "__main__":
    asyncio.run(test())
