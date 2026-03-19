"""
Deep diagnosis of why agent is still timing out despite tools being configured.
Check: ngrok, webhook connectivity, backend logs, agent health.
"""

import httpx
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import time

load_dotenv()

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs")
AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")

print("=" * 80)
print("🔍 ELEVENLABS TOOL EXECUTION DIAGNOSIS")
print("=" * 80)

# ============================================================================
# 1. Check ngrok tunnel
# ============================================================================
print("\n1️⃣ CHECKING NGROK TUNNEL")
print("-" * 80)

try:
    resp = httpx.get(f"{WEBHOOK_URL[:WEBHOOK_URL.rfind('/')]}/health", timeout=5)
    print(f"✅ Ngrok tunnel is ACTIVE")
    print(f"   Status: {resp.status_code}")
except Exception as e:
    print(f"❌ Ngrok tunnel is DOWN")
    print(f"   Error: {e}")

# ============================================================================
# 2. Check webhook endpoint
# ============================================================================
print("\n2️⃣ CHECKING WEBHOOK ENDPOINT")
print("-" * 80)

try:
    # Test webhook with minimal payload
    test_payload = {
        "tool_name": "search_flights",
        "parameters": {
            "destination": "Tokyo"
        }
    }
    
    resp = httpx.post(WEBHOOK_URL, json=test_payload, timeout=5)
    print(f"✅ Webhook is REACHABLE")
    print(f"   Status: {resp.status_code}")
    print(f"   Response: {resp.json()}")
except Exception as e:
    print(f"❌ Webhook is NOT reachable")
    print(f"   URL: {WEBHOOK_URL}")
    print(f"   Error: {e}")

# ============================================================================
# 3. Check agent tool configuration
# ============================================================================
print("\n3️⃣ CHECKING AGENT TOOL CONFIGURATION")
print("-" * 80)

try:
    client = httpx.Client(headers={"xi-api-key": API_KEY}, timeout=10)
    resp = client.get(f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}")
    
    if resp.status_code == 200:
        agent = resp.json()
        tools = agent.get('tools', [])
        print(f"✅ Agent fetched successfully")
        print(f"   Name: {agent.get('name')}")
        print(f"   Tools configured: {len(tools)}")
        
        if len(tools) > 0:
            print(f"\n   Registered tools:")
            for tool in tools:
                webhook_url = tool.get('webhook', {}).get('url', 'N/A')
                print(f"     - {tool.get('tool_name')}")
                print(f"       Webhook: {webhook_url[:60]}...")
        else:
            print(f"   ⚠️ WARNING: 0 tools configured!")
            print(f"   Agent won't call any webhooks if tools aren't registered.")
    else:
        print(f"❌ Failed to fetch agent: {resp.status_code}")
        print(f"   Response: {resp.text[:200]}")
except Exception as e:
    print(f"❌ Error checking agent: {e}")

# ============================================================================
# 4. Check backend logs for webhook calls
# ============================================================================
print("\n4️⃣ CHECKING BACKEND LOGS FOR WEBHOOK CALLS")
print("-" * 80)

logs_dir = Path("logs")
if logs_dir.exists():
    log_files = sorted(logs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if log_files:
        latest_log = log_files[0]
        print(f"Latest log: {latest_log.name}")
        
        try:
            with open(latest_log) as f:
                content = f.read()
                data = json.loads(content)
            
            if isinstance(data, list):
                webhook_calls = [entry for entry in data if "webhook" in str(entry).lower() or "elevenlabs" in str(entry).lower()]
                tool_calls = [entry for entry in data if "tool_name" in str(entry).lower() and "search" in str(entry).lower()]
                
                print(f"   Total log entries: {len(data)}")
                print(f"   Webhook-related: {len(webhook_calls)}")
                print(f"   Tool search calls: {len(tool_calls)}")
                
                if webhook_calls:
                    print(f"\n   Latest webhook call:")
                    latest = webhook_calls[-1]
                    if isinstance(latest, dict):
                        print(f"   {json.dumps(latest, indent=6)[:300]}...")
                else:
                    print(f"\n   ⚠️ NO WEBHOOK CALLS IN LOGS")
                    print(f"   This means the agent is NOT calling tools!")
                
        except Exception as e:
            print(f"   Error reading logs: {e}")
    else:
        print(f"No log files found")
else:
    print(f"No logs directory")

# ============================================================================
# 5. Summary & Diagnosis
# ============================================================================
print("\n" + "=" * 80)
print("📋 DIAGNOSIS SUMMARY")
print("=" * 80)

print("""
Possible Reasons Why Agent is Still Timing Out:

1. 🔴 CRITICAL: Agent doesn't know to USE the tools
   - Tools are registered ✅
   - System prompt mentions tools ✅
   - BUT: Agent might not be programmed to call them
   - FIX: Need better system prompt that explicitly guides agent to search first

2. 🔴 CRITICAL: Tool webhook URLs might be wrong
   - Check that webhook URL in ElevenLabs tools matches your ngrok URL
   - Current ngrok: https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs
   - If ngrok URL changed, tools need to be updated

3. 🟡 MEDIUM: Agent is waiting for clarification
   - Customer says: "booking a new flight"
   - Agent might ask: "Where do you want to go?"
   - Scenario expects specific destination but customer didn't say it

4. 🟡 MEDIUM: Agent timing out at ElevenLabs side
   - ElevenLabs service might have issues
   - Agent WebSocket connection might be unstable

NEXT STEPS:
1. Check backend logs (see output above for webhook calls)
2. Verify ngrok tunnel is active (run: python start_ngrok.py)
3. Update system prompt with STRONGER guidance to search_flights first
4. Check ElevenLabs agent logs/activity in dashboard

ACTION ITEMS:
- If NO webhook calls in logs: Agent doesn't know to use tools (fix system prompt)
- If webhook calls ARE there: Backend issue (check webhook handler)
- If ngrok is down: Restart ngrok and update tools webhook URLs
""")

print("\n🔗 KEY URLs:")
print(f"   Ngrok Health: {WEBHOOK_URL[:WEBHOOK_URL.rfind('/')]}/health")
print(f"   Webhook: {WEBHOOK_URL}")
print(f"   Backend: http://localhost:8000/health")
print(f"   Agent Dashboard: https://elevenlabs.io/app/conversational-ai")
