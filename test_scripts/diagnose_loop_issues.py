"""
Diagnose critical loop issues:
1. Is ElevenLabs agent receiving tool calls?
2. Is webhook receiving requests?
3. What's happening with Gemini response truncation?
"""

import httpx
import json
from datetime import datetime
from pathlib import Path

def check_backend_status():
    """Check backend health and endpoints"""
    print("\n" + "="*80)
    print("🔍 BACKEND STATUS CHECK")
    print("="*80)
    
    try:
        resp = httpx.get("http://localhost:8000/health", timeout=5)
        print(f"✅ Backend healthy: {resp.json()}")
    except Exception as e:
        print(f"❌ Backend error: {e}")
    
def check_agent_configuration():
    """Check ElevenLabs agent settings"""
    print("\n" + "="*80)
    print("🔍 ELEVENLABS AGENT CONFIGURATION")
    print("="*80)
    
    from dotenv import load_dotenv
    import os
    load_dotenv()
    
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")
    api_key = os.getenv("ELEVENLABS_API_KEY")
    
    print(f"Agent ID: {agent_id}")
    print(f"API Key Present: {'✅' if api_key else '❌'}")
    
    # Fetch agent details
    try:
        resp = httpx.get(
            f"https://api.elevenlabs.io/v1/convai/agents/{agent_id}",
            headers={"xi-api-key": api_key},
            timeout=10
        )
        if resp.status_code == 200:
            agent_data = resp.json()
            print(f"\n✅ Agent found:")
            print(f"  Name: {agent_data.get('name')}")
            print(f"  Status: {agent_data.get('status')}")
            print(f"  System Prompt (first 200 chars):")
            prompt = agent_data.get('system_prompt', '')
            print(f"    {prompt[:200]}...")
            
            # Check tools
            tools = agent_data.get('tools', [])
            print(f"\n  Tools configured: {len(tools)}")
            for i, tool in enumerate(tools, 1):
                print(f"    {i}. {tool.get('tool_name')} - webhook @ {tool.get('webhook').get('url')[:60]}...")
        else:
            print(f"❌ Failed to fetch agent: {resp.status_code}")
            print(resp.text[:500])
    except Exception as e:
        print(f"❌ Error fetching agent: {e}")

def check_webhook_logs():
    """Check if webhook is receiving requests"""
    print("\n" + "="*80)
    print("🔍 WEBHOOK ACTIVITY CHECK")
    print("="*80)
    
    # Check if there's a webhook log file
    logs_dir = Path("logs")
    if logs_dir.exists():
        json_files = sorted(logs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        if json_files:
            latest_log = json_files[0]
            print(f"\nLatest log file: {latest_log.name}")
            
            try:
                with open(latest_log) as f:
                    logs = json.load(f)
                
                if isinstance(logs, list):
                    webhook_calls = [l for l in logs if 'webhook' in str(l).lower()]
                    tool_calls = [l for l in logs if 'tool' in str(l).lower() or 'search_flights' in str(l).lower()]
                    
                    print(f"  Total entries: {len(logs)}")
                    print(f"  Webhook entries: {len(webhook_calls)}")
                    print(f"  Tool calls: {len(tool_calls)}")
                    
                    if webhook_calls:
                        print(f"\n  Latest webhook call:")
                        print(f"    {json.dumps(webhook_calls[-1], indent=2)[:300]}...")
                    else:
                        print(f"\n  ⚠️ No webhook calls found in logs!")
                    
                    if tool_calls:
                        print(f"\n  Latest tool call:")
                        print(f"    {json.dumps(tool_calls[-1], indent=2)[:300]}...")
            except json.JSONDecodeError:
                print(f"  ❌ Could not parse log file")
        else:
            print("  No log files found")
    else:
        print("  No logs directory")

def check_elevenlabs_response_handling():
    """Check how Gemini responses are being parsed"""
    print("\n" + "="*80)
    print("🔍 GEMINI RESPONSE HANDLING")
    print("="*80)
    
    print("""
Current Issue: Gemini evaluation returns truncated JSON
  - Response cuts off mid-string in the "rationale" field
  - Causes: "Unterminated string starting at: line 5 column 20"

Likely Causes:
1. ❌ Gemini response token limit exceeded (context too large)
2. ❌ Response streaming cut off early
3. ❌ JSON formatting issue in Gemini prompt

Fix Strategy:
1. Check evaluator.py for response size limits
2. Add response truncation handling
3. Review Gemini system prompt for evaluation
4. Add fallback parsing for incomplete JSON
""")

def check_elevenlabs_timeout_issue():
    """Analyze the ElevenLabs timeout pattern"""
    print("\n" + "="*80)
    print("🔍 ELEVENLABS RESPONSE TIMEOUT PATTERN")
    print("="*80)
    
    print("""
Observed Pattern Across All Iterations:
1. ✅ Agent connects via WebSocket
2. ✅ Initial greeting received: "Hello! How can I help you today?"
3. ❌ Customer puts booking request
4. ❌ Agent doesn't respond (25s timeout → 30s timeout)
5. ❌ WebSocket closes with protocol error

Possible Causes:
1. 🔴 CRITICAL: Agent prompt doesn't include tool instructions
   - Agent doesn't know WHAT tools are available
   - Agent doesn't know HOW to call them
   - Customer message received but agent can't respond

2. 🔴 CRITICAL: Webhook not configured properly in agent
   - Tools exist but webhook URL is wrong/unreachable
   - Agent tries to call tool but can't reach backend

3. 🟡 MEDIUM: Poor prompt design
   - System prompt doesn't guide agent to search/book flights
   - Agent waits for clarification that never comes

4. 🟡 MEDIUM: ElevenLabs API quota/rate limit
   - Agent service throttled or rate-limited
   - Check ElevenLabs dashboard for usage

Fix Strategy:
1. ⭐ First: Verify agent's system prompt includes tool usage instructions
2. ⭐ First: Verify webhook URL is correct and reachable
3. ⭐ First: Check ElevenLabs agent logs/activity
4. Second: Review evaluator.py for JSON response handling
5. Second: Add detailed logging to webhook to see tool calls
""")

def main():
    print("\n\n")
    print("█" * 80)
    print("AUTONOMOUS LOOP DIAGNOSTIC REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("█" * 80)
    
    check_backend_status()
    check_agent_configuration()
    check_webhook_logs()
    check_elevenlabs_response_handling()
    check_elevenlabs_timeout_issue()
    
    print("\n" + "="*80)
    print("🎯 RECOMMENDED NEXT STEPS")
    print("="*80)
    print("""
1. CHECK ELEVENLABS AGENT SYSTEM PROMPT:
   - Does it mention the flight booking tools?
   - Does it include instructions on how to use the tools?
   - Expected: "You have access to tools: search_flights, book_flight, etc."

2. VERIFY WEBHOOK CONNECTIVITY:
   - Test: curl https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs
   - Check if ngrok tunnel is still live
   - Check if backend webhook handler is working

3. ADD WEBHOOK REQUEST LOGGING:
   - Currently: Maybe no tool calls reaching the webhook
   - Solution: Add logging to webhook handler to see incoming requests

4. FIX GEMINI JSON TRUNCATION:
   - Add response size validation in evaluator.py
   - Handle incomplete JSON gracefully
   - Set stricter GPT response size limits

5. TEST ELEVENLABS AGENT DIRECTLY:
   - Use ElevenLabs sandbox/UI to test agent
   - Verify it can search for flights and book them
   - Confirm tool integration works
""")

if __name__ == "__main__":
    main()
