# 🚀 ElevenLabs Agent Tool Configuration Guide

## Issue Summary

The autonomous refinement loop has started, but the **ElevenLabs agent has NO tools configured**.

**Symptom**: Agent responds with greeting ("Hello! How can I help you today?") but then times out when customer tries to book a flight.

**Root Cause**: ElevenLabs agent must have explicit tool registrations to make webhook calls. The agent has been given tool instructions in its system prompt, but the tools themselves are not registered.

---

## 🔴 Critical Issue: 0 Tools Configured

```
✅ Agent found: "Airline Assistant Agent"
❌ Tools configured: 0
```

The agent **needs 9 tools registered**:
1. search_flights
2. book_flight
3. get_booking
4. cancel_booking
5. reschedule_booking
6. add_extras
7. add_assistance
8. get_flight_status
9. get_policy

---

## ✅ What We've Fixed

### 1. System Prompt Updated ✅
- Added complete tool instructions to agent's system prompt
- Agent now knows about each tool and when to use it
- File: `update_agent_system_prompt.py` executed successfully

### 2. Gemini Evaluation Response Truncation Fixed ✅
- Increased `max_output_tokens` from 1024 to 2048
- Added fallback JSON recovery for truncated responses
- File: `refinement_loop/evaluator.py` updated

### 3. Backend Webhook Ready ✅
- Webhook endpoint at: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- Backend server running on port 8000
- Database initialized with 33 flights

---

## 🔧 How to Configure Tools (Manual)

### Option A: ElevenLabs UI (Recommended)

1. **Open ElevenLabs Dashboard**
   - Go to: https://elevenlabs.io/app/conversational-ai

2. **Select Your Agent**
   - Find: "Airline Assistant Agent"
   - ID: `agent_8801km2b8g2ge4d8n2dpjsf3txvp`

3. **Add Tools**
   - Look for "Tools" section or "Add Tool" button
   - For each of the 9 tools below, click "Add Tool"

4. **Tool Configuration**

**Tool 1: search_flights**
```json
{
  "tool_name": "search_flights",
  "description": "Search for available flights",
  "parameters": {
    "type": "object",
    "properties": {
      "destination": {"type": "string", "description": "Destination city"},
      "date": {"type": "string", "description": "YYYY-MM-DD format"},
      "seat_class": {"type": "string", "description": "economy/business/first"}
    },
    "required": ["destination"]
  },
  "webhook": {
    "url": "https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs",
    "method": "POST"
  }
}
```

**Tool 2: book_flight**
```json
{
  "tool_name": "book_flight",
  "description": "Book a flight for a customer",
  "parameters": {
    "type": "object",
    "properties": {
      "flight_id": {"type": "string"},
      "passenger_name": {"type": "string"},
      "email": {"type": "string"},
      "seat_class": {"type": "string"}
    },
    "required": ["flight_id", "passenger_name", "email"]
  },
  "webhook": {
    "url": "https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs",
    "method": "POST"
  }
}
```

*(Repeat for remaining 7 tools - see ELEVENLABS_TOOLS_CONFIG.json for complete definitions)*

5. **Save and Test**
   - Save all tool configurations
   - The agent should now call tools via webhook

---

### Option B: Verify Ngrok Tunnel is Active

Before tools can work, ensure the webhook URL is reachable:

```powershell
# Test webhook connectivity
curl https://semiacidified-pansophistically-charmain.ngrok-free.dev/health
# Should return: {"status": "healthy"}
```

If ngrok tunnel is down:
```powershell
python start_ngrok.py
```

---

## 📋 Complete Tool Configurations

All 9 tools are defined in: **`ELEVENLABS_TOOLS_CONFIG.json`**

You can copy-paste individual tool definitions from that file into the ElevenLabs UI.

---

## 🔄 After Configuring Tools

### 1. Restart the Loop

Once tools are configured in ElevenLabs, restart the loop:

```powershell
python run_and_monitor_loop.py
```

### 2. Monitor Webhook Calls

Watch backend logs for tool calls:

```powershell
# In a terminal, check backend output:
# You should see:
# 2026-03-19 11:59:00 [INFO] ElevenLabs webhook received: {'tool_name': 'search_flights', ...}
```

### 3. Verify Success

Loop should now:
- ✅ Agent processes customer request
- ✅ Agent calls search_flights tool
- ✅ Backend returns flights
- ✅ Agent confirms booking
- ✅ Iteration completes with score > 0.0

---

## 🐛 Troubleshooting

### Tools Still Not Calling?

**Check 1: Webhook URL Reachable?**
```powershell
curl https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs
# Should return: {"result": "ERROR: Could not determine which tool to call..."}
# (This is OK - it means webhook is reachable)
```

**Check 2: Tools Saved in ElevenLabs?**
- Go to agent settings
- Verify 9 tools are listed

**Check 3: Webhook Logs**
```powershell
# Check if backend is receiving any requests:
# Look for: "ElevenLabs webhook received:"
# If NOT seeing this, tools aren't configured in agent
```

**Check 4: Ngrok Tunnel**
```powershell
# Ensure ngrok is running:
python start_ngrok.py
# Your URL: https://semiacidified-pansophistically-charmain.ngrok-free.dev
```

---

## 📊 Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| Backend Server | ✅ Running | localhost:8000 |
| Ngrok Tunnel | ✅ Live | semiacidified-pansophistically-charmain.ngrok-free.dev |
| Database | ✅ Ready | 33 flights, 15+ bookings |
| Webhook Handler | ✅ Enabled | /webhook/elevenlabs |
| Agent System Prompt | ✅ Updated | Includes tool instructions |
| Agent Tools | ❌ **0/9** | **← NEEDS MANUAL CONFIG** |
| Loop | ✅ Running | Waiting for tool responses |

---

## 🎯 Next Steps (In Order)

### 1. [5 min] Configure Tools in ElevenLabs UI
   - Manual: Add 9 tools via UI  
   - Automated: (Not available with current API)

### 2. [1 min] Restart Loop
   ```powershell
   python run_and_monitor_loop.py
   ```

### 3. [~5-15 min] Monitor Progress
   - Watch for tool calls in backend logs
   - Monitor iteration scores
   - Loop should complete with scores > 0.0

### 4. [~30 min] Full Loop Completion
   - Expected: 5 iterations max, 8.0 pass threshold
   - Success: Agent books flights autonomously
   - Failure patterns: Identified and fixed by refinement loop

---

## 📝 Files Modified This Session

| File | Change | Status |
|------|--------|--------|
| `refinement_loop/evaluator.py` | Increased token limit, added JSON recovery | ✅ Done |
| `update_agent_system_prompt.py` | Created tool instruction updater | ✅ Done |
| `ELEVENLABS_TOOLS_CONFIG.json` | Generated complete tool configs | ✅ Done |

---

## 🚀 Expected Behavior After Tools Configured

1. **Loop starts**: `python run_and_monitor_loop.py`
2. **Iteration 1**: 
   - Simulation: Customer: "I'd like to book a flight"
   - Agent calls: `search_flights(destination="Tokyo")`
   - Webhook receives call ✅
   - Backend returns flights ✅
   - Agent confirms booking ✅
   - Evaluation scores ✅
3. **Iterations 2-5**: Improve if needed
4. **Final**: Score > 8.0 (success) or fixes applied

---

## 💡 Key Insights

### Why Tools Weren't Configured?

ElevenLabs ConvAI requires explicit tool registration in three ways:
1. **Agents API** (attempted): Returns 404 - this endpoint doesn't exist for tool management
2. **Dashboard UI** (recommended): Manual tool addition in web interface
3. **System Prompt** (done): Guides agent on tool usage (but doesn't register webhooks)

The system prompt helps the agent understand WHAT tools to use, but ElevenLabs still requires explicit tool registration for WEBHOOK CALLING.

### Why Agent Times Out?

Agent knows about tools from system prompt, but:
- No webhook URL is configured for tools
- Agent can't make HTTP calls to backend
- Agent waits indefinitely for no response
- Connection times out after 30s

### Solution Path

System prompt (✅ Done) + Tool registration (❌ Pending) = Full integration ✅

---

## 📞 Support

If tools don't work after manual configuration:
1. Check ngrok tunnel is running
2. Test webhook: `curl https://...../webhook/elevenlabs`
3. Check backend logs for "ElevenLabs webhook received:"
4. Verify tool names match exactly (case-sensitive)
5. Check parameter names: `destination`, `ref`, `flight_id` (not variations)
