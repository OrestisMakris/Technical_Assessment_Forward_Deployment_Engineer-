"""
Simple conversation - write output to file so we can see what happened
"""

import asyncio
import json
import sys
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

output = []

def log(msg):
    output.append(msg)
    print(msg, flush=True)
    sys.stdout.flush()

async def main():
    log("=" * 80)
    log("CONVERSATION TEST")
    log("=" * 80)
    log("")
    
    try:
        uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
        log(f"Connecting to: {uri[:50]}...")
        
        async with websockets.connect(uri, additional_headers={"xi-api-key": API_KEY}) as ws:
            log("✅ Connected")
            
            # Handshake
            log("\n📤 Handshake...")
            await ws.send(json.dumps({
                "type": "conversation_initiation_client_data",
                "conversation_config_override": {
                    "agent": {"enable_model_fallback": False},
                    "client_tool_result": {"notification_level": "silent"},
                },
            }))
            
            # Get greeting
            log("📥 Waiting for greeting (10s)...")
            greeting = ""
            try:
                for _ in range(100):
                    msg_raw = await asyncio.wait_for(ws.recv(), timeout=0.1)
                    msg = json.loads(msg_raw)
                    if msg.get('type') == 'agent_response':
                        greeting = msg.get('agent_response_event', {}).get('agent_response', '')
                        if greeting:
                            log(f"✅ Greeting: {greeting}")
                            break
            except asyncio.TimeoutError:
                log("⏱️  Timeout on greeting")
            
            if greeting:
                # Send message
                log("\n📤 Sending: 'I want to book a flight to Tokyo'")
                await ws.send(json.dumps({
                    "type": "user_turn",
                    "user_turn": {"text": "I want to book a flight to Tokyo"},
                }))
                
                # Get response
                log("📥 Waiting for response (30s)...")
                response = ""
                try:
                    for _ in range(300):
                        msg_raw = await asyncio.wait_for(ws.recv(), timeout=0.1)
                        msg = json.loads(msg_raw)
                        if msg.get('type') == 'agent_response':
                            response = msg.get('agent_response_event', {}).get('agent_response', '')
                            if response:
                                log(f"✅ Response: {response}")
                                break
                except asyncio.TimeoutError:
                    log("⏱️  Timeout on response")
                
                if not response:
                    log("❌ No response received")
            else:
                log("❌ No greeting")
    
    except Exception as e:
        log(f"❌ ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc(file=open("/tmp/error.txt", "w"))
    
    # Write output to file
    with open("conversation_test_output.txt", "w") as f:
        f.write("\n".join(output))
    
    log("\n✅ Output written to conversation_test_output.txt")

if __name__ == "__main__":
    asyncio.run(main())
