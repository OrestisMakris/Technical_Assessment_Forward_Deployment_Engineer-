"""
Debug: Check exact message sequence after handshake
"""

import asyncio
import json
from dotenv import load_dotenv
import os

try:
    import websockets
except:
    import subprocess
    subprocess.check_call(["pip", "install", "websockets", "-q"])
    import websockets

load_dotenv()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

async def main():
    print("Connecting...")
    
    uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
    
    async with websockets.connect(uri, additional_headers={"xi-api-key": API_KEY}) as ws:
        print("OK")
        
        # Handshake
        print("Handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {"enable_model_fallback": False},
                "client_tool_result": {"notification_level": "silent"},
            },
        }))
        
        # Listen with longer timeout
        print("\nWaiting (30s)...")
        msg_count = 0
        
        try:
            while msg_count < 100:
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)  # 1 sec timeout per message
                msg_count += 1
                msg = json.loads(msg_raw)
                msg_type = msg.get('type', 'unknown')
                
                if msg_type == 'agent_response':
                    text = msg.get('agent_response_event', {}).get('agent_response', '')
                    print(f"{msg_count}. GREETING: {text}")
                elif msg_type == 'agent_chat_response_part':
                    print(f"{msg_count}. agent_chat_response_part")
                elif msg_type == 'ping':
                    print(f"{msg_count}. ping")
                else:
                    print(f"{msg_count}. {msg_type}")
        
        except asyncio.TimeoutError:
            print(f"\nTimeout after {msg_count} messages")

if __name__ == "__main__":
    asyncio.run(main())
