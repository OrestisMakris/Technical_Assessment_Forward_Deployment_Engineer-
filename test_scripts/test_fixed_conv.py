"""
Test conversation after fixing agent_chat_response_part handling
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
    print("=" * 80)
    print("TESTING CONVERSATION AFTER FIXING agent_chat_response_part")
    print("=" * 80)
    print("")
    
    try:
        uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
        
        async with websockets.connect(uri, additional_headers={"xi-api-key": API_KEY}) as ws:
            print("OK Connected")
            
            # Handshake
            print("Sending handshake...")
            await ws.send(json.dumps({
                "type": "conversation_initiation_client_data",
                "conversation_config_override": {
                    "agent": {"enable_model_fallback": False},
                    "client_tool_result": {"notification_level": "silent"},
                },
            }))
            
            # Get greeting (now properly handles agent_chat_response_part)
            print("Listening for greeting (15s)...")
            greeting = ""
            msg_count = 0
            
            try:
                while msg_count < 200:
                    msg_raw = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    msg_count += 1
                    msg = json.loads(msg_raw)
                    msg_type = msg.get('type')
                    
                    if msg_type == 'agent_response':
                        greeting = msg.get('agent_response_event', {}).get('agent_response', '')
                        if greeting:
                            print(f"Got greeting: {greeting}")
                            break
                    elif msg_type == 'agent_chat_response_part':
                        print(f"  (building response part {msg_count}...)")
            except asyncio.TimeoutError:
                print("Timeout")
            
            if greeting:
                # Send customer message
                print("\nSending customer message...")
                await ws.send(json.dumps({
                    "type": "user_turn",
                    "user_turn": {"text": "I want to book a flight to Tokyo"},
                }))
                
                # Get response
                print("Waiting for response (20s)...")
                response = ""
                msg_count = 0
                
                try:
                    while msg_count < 200:
                        msg_raw = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        msg_count += 1
                        msg = json.loads(msg_raw)
                        msg_type = msg.get('type')
                        
                        if msg_type == 'agent_response':
                            response = msg.get('agent_response_event', {}).get('agent_response', '')
                            if response:
                                print(f"Got response: {response}")
                                break
                        elif msg_type == 'agent_chat_response_part':
                            print(f"  (building response part {msg_count}...)")
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                
                if response:
                    print(f"\nSUCCESS! Agent responded to customer message:")
                    print(f"  Customer: 'I want to book a flight to Tokyo'")
                    print(f"  Agent: '{response}'")
                else:
                    print("\nFAILED - No response to customer message")
            else:
                print("\nFAILED - No greeting")
    
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
