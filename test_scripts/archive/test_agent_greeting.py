"""
Test if agent sends the initial greeting properly.
Monitor all WebSocket messages to see what the agent actually sends.
"""

import asyncio
import json
import logging
from dotenv import load_dotenv
import os

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess
    subprocess.check_call(["pip", "install", "websockets"])
    import websockets

load_dotenv()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_agent_greeting():
    """Test agent's initial greeting and all WebSocket messages."""
    
    print("=" * 80)
    print("🔍 TESTING AGENT INITIAL GREETING")
    print("=" * 80)
    
    if not AGENT_ID or not API_KEY:
        print("❌ Missing ELEVENLABS_AGENT_ID or ELEVENLABS_API_KEY")
        return
    
    try:
        uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
        
        print(f"\n📡 Connecting to: {uri}")
        
        async with websockets.connect(uri) as websocket:
            print(f"✅ Connected to ElevenLabs WebSocket")
            
            # Send conversation initiation
            init_msg = {
                "type": "conversation_initiation_client_data",
                "conversation_config_override": {
                    "agent": {
                        "prompt": {
                            "prompt": ""
                        }
                    }
                }
            }
            
            await websocket.send(json.dumps(init_msg))
            print(f"\n📤 Sent: conversation_initiation_client_data")
            
            # Listen for all incoming messages
            print(f"\n⏳ Listening for messages (30 second timeout)...")
            print("=" * 80)
            
            message_count = 0
            agent_greeting = None
            
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30)
                    message_count += 1
                    
                    try:
                        msg = json.loads(response)
                        msg_type = msg.get('type', 'unknown')
                        
                        print(f"\n📥 Message #{message_count} - Type: {msg_type}")
                        
                        # Print the full message structure
                        print(f"Content: {json.dumps(msg, indent=2)[:400]}...")
                        
                        # Check for agent greeting
                        if msg_type == 'agent_response':
                            agent_response = msg.get('agent_response_event', {}).get('agent_response', '')
                            if agent_response:
                                agent_greeting = agent_response
                                print(f"\n🤖 AGENT GREETING FOUND:")
                                print(f"   {agent_greeting}")
                        
                        # Check for other important message types
                        if msg_type == 'user_input_need':
                            print(f"⚠️  Agent needs user input")
                        elif msg_type == 'conversation_ended':
                            print(f"⚠️  Conversation ended")
                            break
                        elif msg_type == 'internal_server_error':
                            print(f"❌ Server error: {msg}")
                            break
                    
                    except json.JSONDecodeError as e:
                        print(f"⚠️  Failed to parse JSON: {e}")
                        print(f"Raw response: {response[:200]}")
            
            except asyncio.TimeoutError:
                print(f"\n⏱️  Timeout after listening for 30 seconds")
            
            print("\n" + "=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Total messages received: {message_count}")
            
            if agent_greeting:
                print(f"✅ Agent greeting: {agent_greeting}")
            else:
                print(f"❌ NO AGENT GREETING RECEIVED")
            
            # Now try sending a customer message
            if message_count > 0:
                print(f"\n📤 Sending customer message...")
                user_turn = {
                    "type": "user_turn",
                    "user_turn": {
                        "text": "Hi, I'd like to book a flight to Tokyo please."
                    }
                }
                
                await websocket.send(json.dumps(user_turn))
                print(f"✅ Customer message sent")
                
                # Wait for response
                print(f"\n⏳ Waiting for agent response (15 seconds)...")
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=15)
                    msg = json.loads(response)
                    
                    if msg.get('type') == 'agent_response':
                        agent_msg = msg.get('agent_response_event', {}).get('agent_response', '')
                        print(f"\n🤖 AGENT RESPONSE:")
                        print(f"   {agent_msg}")
                    else:
                        print(f"📥 Response type: {msg.get('type')}")
                        print(f"   {json.dumps(msg, indent=2)[:300]}...")
                
                except asyncio.TimeoutError:
                    print(f"⏱️  No response within 15 seconds")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_greeting())
