"""
Test the agent's actual response with the new prompt.
Check if agent generates realistic flight options as instructed.
"""

import asyncio
import json
import logging
import websockets
import base64
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

async def test_agent_response():
    """Test agent's actual response to a booking request."""
    
    print("=" * 80)
    print("🔍 TESTING AGENT RESPONSE WITH NEW PROMPT")
    print("=" * 80)
    
    # First, fetch the current prompt to verify it's active
    print("\n1️⃣ CHECKING CURRENT SYSTEM PROMPT")
    print("-" * 80)
    
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}",
                headers={"xi-api-key": API_KEY}
            )
            
            if resp.status_code == 200:
                agent = resp.json()
                prompt = agent.get('conversation_config', {}).get('agent', {}).get('prompt', {}).get('prompt', '')
                
                print(f"✅ Agent prompt ({len(prompt)} chars):")
                print(f"\n{prompt[:400]}...")
                
                # Check if new prompt is active
                if "GENERATE realistic flight options" in prompt:
                    print(f"\n✅ NEW PROMPT IS ACTIVE (contains: 'GENERATE realistic flight options')")
                else:
                    print(f"\n⚠️ Prompt doesn't contain expected text")
            else:
                print(f"❌ Failed to fetch agent: {resp.status_code}")
                return
    except Exception as e:
        print(f"❌ Error fetching agent: {e}")
        return
    
    # Now test the agent's response
    print("\n" + "=" * 80)
    print("2️⃣ TESTING AGENT RESPONSE TO BOOKING REQUEST")
    print("-" * 80)
    
    try:
        uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
        
        async with websockets.connect(uri) as websocket:
            print(f"\n✅ Connected to ElevenLabs WebSocket")
            
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
            print(f"📤 Sent conversation initiation")
            
            # Wait for initial greeting
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            msg = json.loads(response)
            
            if msg.get('type') == 'agent_response':
                greeting = msg.get('agent_response_event', {}).get('agent_response', '')
                print(f"\n👤 AGENT GREETING:")
                print(f"   {greeting}")
            
            # Send customer message - booking request
            customer_msg = "Hi, I'd like to book a flight to Tokyo please."
            
            print(f"\n👥 CUSTOMER MESSAGE:")
            print(f"   {customer_msg}")
            
            user_turn = {
                "type": "user_turn",
                "user_turn": {
                    "text": customer_msg
                }
            }
            
            await websocket.send(json.dumps(user_turn))
            print(f"📤 Sent customer message")
            
            # Receive agent response
            print(f"\n⏳ Waiting for agent response (up to 60s)...")
            
            agent_response = ""
            response_complete = False
            
            while not response_complete:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60)
                    msg = json.loads(response)
                    
                    if msg.get('type') == 'agent_response':
                        agent_response = msg.get('agent_response_event', {}).get('agent_response', '')
                        if agent_response:
                            print(f"\n🤖 AGENT RESPONSE:")
                            print(f"   {agent_response}")
                            response_complete = True
                    elif msg.get('type') == 'conversation_ended':
                        print(f"⚠️ Conversation ended")
                        response_complete = True
                except asyncio.TimeoutError:
                    print(f"⏱️ Timeout waiting for response")
                    response_complete = True
            
            # Analyze response
            print(f"\n" + "=" * 80)
            print("3️⃣ ANALYZING AGENT RESPONSE")
            print("-" * 80)
            
            if agent_response:
                checks = {
                    "Mentions flights": "flight" in agent_response.lower(),
                    "Shows options": ("option" in agent_response.lower() or 
                                    "available" in agent_response.lower()),
                    "Has pricing": "$" in agent_response or "price" in agent_response.lower(),
                    "Has times": (":" in agent_response and "0" in agent_response),
                    "References Tokyo": "tokyo" in agent_response.lower(),
                }
                
                print(f"\nResponse quality checks:")
                for check, result in checks.items():
                    status = "✅" if result else "❌"
                    print(f"  {status} {check}")
                
                # Overall assessment
                passed = sum(1 for v in checks.values() if v)
                print(f"\nScore: {passed}/{len(checks)} checks passed")
                
                if passed >= 4:
                    print(f"\n✅ AGENT IS WORKING! Generating realistic responses.")
                else:
                    print(f"\n⚠️ Agent response quality could be better")
            else:
                print(f"❌ No response received from agent")
    
    except asyncio.TimeoutError:
        print(f"❌ Timeout connecting to WebSocket")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_response())
