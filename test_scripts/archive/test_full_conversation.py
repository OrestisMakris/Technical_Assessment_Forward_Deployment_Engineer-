"""
Full conversation test:
1. Connect and get greeting
2. Send customer message
3. Get agent response
4. Send another customer message
5. Get agent response
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

async def run_conversation():
    print("=" * 80)
    print("🔍 FULL CONVERSATION TEST")
    print("=" * 80)
    print("")
    
    uri = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={AGENT_ID}"
    
    async with websockets.connect(uri, additional_headers={"xi-api-key": API_KEY}) as ws:
        print("✅ Connected\n")
        
        # === STEP 1: HANDSHAKE ===
        print("📤 STEP 1: Sending handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {"enable_model_fallback": False},
                "client_tool_result": {"notification_level": "silent"},
            },
        }))
        
        # === STEP 2: GET GREETING ===
        print("📥 Waiting for greeting...\n")
        
        greeting = None
        frame_count = 0
        
        try:
            while frame_count < 100:  # safety limit
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                frame_count += 1
                
                try:
                    msg = json.loads(msg_raw)
                    msg_type = msg.get('type', '')
                    
                    if msg_type == 'agent_response':
                        greeting = msg.get('agent_response_event', {}).get('agent_response', '')
                        if greeting:
                            print(f"🤖 AGENT GREETING:")
                            print(f"   '{greeting}'\n")
                            break
                    elif msg_type == 'ping':
                        pass  # skip pings
                    elif msg_type not in ['conversation_initiation_metadata', 'agent_chat_response_part', 'audio']:
                        pass
                
                except json.JSONDecodeError:
                    pass
        
        except asyncio.TimeoutError:
            print("❌ Timeout waiting for greeting\n")
        
        if not greeting:
            print("❌ Did not receive greeting. Exiting.\n")
            return
        
        # === STEP 3: SEND FIRST CUSTOMER MESSAGE ===
        print("=" * 80)
        print("📤 STEP 2: Sending customer message...")
        customer_msg_1 = "Hello! I'd like to book a flight to Tokyo please."
        print(f"   Customer: '{customer_msg_1}'\n")
        
        await ws.send(json.dumps({
            "type": "user_turn",
            "user_turn": {"text": customer_msg_1},
        }))
        
        # === STEP 4: GET FIRST AGENT RESPONSE ===
        print("📥 Waiting for agent response (30 seconds)...\n")
        
        agent_response_1 = None
        frame_count = 0
        last_content_time = asyncio.get_running_loop().time()
        
        try:
            while frame_count < 200:
                try:
                    msg_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    frame_count += 1
                    current_time = asyncio.get_running_loop().time()
                    
                    try:
                        msg = json.loads(msg_raw)
                        msg_type = msg.get('type', '')
                        
                        if msg_type == 'agent_response':
                            agent_response_1 = msg.get('agent_response_event', {}).get('agent_response', '')
                            if agent_response_1:
                                print(f"🤖 AGENT RESPONSE 1:")
                                print(f"   '{agent_response_1}'\n")
                                last_content_time = current_time
                                break
                        elif msg_type == 'audio':
                            chars = msg.get('audio_event', {}).get('alignment', {}).get('chars', [])
                            if chars:
                                char_str = ''.join(chars)
                                if char_str.strip():
                                    last_content_time = current_time
                        elif msg_type == 'ping':
                            pass
                    
                    except json.JSONDecodeError:
                        pass
                
                except asyncio.TimeoutError:
                    # Check if silence timeout exceeded
                    if asyncio.get_running_loop().time() - last_content_time > 2.0:
                        print("📭 (30 second silence - assuming agent finished)\n")
                        break
        
        except Exception as e:
            print(f"❌ Error: {e}\n")
            agent_response_1 = None
        
        if not agent_response_1:
            print("❌ No agent response received\n")
        else:
            # === STEP 5: SEND SECOND CUSTOMER MESSAGE ===
            print("=" * 80)
            print("📤 STEP 3: Sending follow-up customer message...")
            customer_msg_2 = "Great! Can you book me on flight FL-201?"
            print(f"   Customer: '{customer_msg_2}'\n")
            
            await ws.send(json.dumps({
                "type": "user_turn",
                "user_turn": {"text": customer_msg_2},
            }))
            
            # === STEP 6: GET SECOND AGENT RESPONSE ===
            print("📥 Waiting for agent response (30 seconds)...\n")
            
            agent_response_2 = None
            frame_count = 0
            last_content_time = asyncio.get_running_loop().time()
            
            try:
                while frame_count < 200:
                    try:
                        msg_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                        frame_count += 1
                        current_time = asyncio.get_running_loop().time()
                        
                        try:
                            msg = json.loads(msg_raw)
                            msg_type = msg.get('type', '')
                            
                            if msg_type == 'agent_response':
                                agent_response_2 = msg.get('agent_response_event', {}).get('agent_response', '')
                                if agent_response_2:
                                    print(f"🤖 AGENT RESPONSE 2:")
                                    print(f"   '{agent_response_2}'\n")
                                    last_content_time = current_time
                                    break
                            elif msg_type == 'audio':
                                chars = msg.get('audio_event', {}).get('alignment', {}).get('chars', [])
                                if chars:
                                    char_str = ''.join(chars)
                                    if char_str.strip():
                                        last_content_time = current_time
                            elif msg_type == 'ping':
                                pass
                        
                        except json.JSONDecodeError:
                            pass
                    
                    except asyncio.TimeoutError:
                        if asyncio.get_running_loop().time() - last_content_time > 2.0:
                            print("📭 (30 second silence - assuming agent finished)\n")
                            break
            
            except Exception as e:
                print(f"❌ Error: {e}\n")
                agent_response_2 = None
        
        # === SUMMARY ===
        print("=" * 80)
        print("CONVERSATION SUMMARY")
        print("=" * 80)
        
        if greeting:
            print(f"✅ Greeting received: '{greeting}'")
        else:
            print(f"❌ No greeting")
        
        if agent_response_1:
            print(f"✅ Response 1 received")
        else:
            print(f"❌ No response to message 1")
        
        if agent_response_1 and agent_response_2:
            print(f"✅ Response 2 received")
        else:
            if agent_response_1:
                print(f"❌ No response to message 2")

if __name__ == "__main__":
    asyncio.run(run_conversation())
