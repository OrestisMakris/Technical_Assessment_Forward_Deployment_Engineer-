## Troubleshooting: ElevenLabs Agent Not Capturing Conversations

### Problem
The refinement loop runs but the agent only shows audio metadata ("Unknown" entries in ElevenLabs dashboard) instead of actual conversation transcripts. The loop cannot capture conversation text to evaluate.

### Root Causes & Solutions

#### 1. **Incorrect WebSocket Message Format** ✅ FIXED
**Symptom:** Agent receives text but doesn't process it correctly
**Fix Applied:**
- Text injections must use the format: `{"type": "user_turn", "user_turn": {"text": "..."}}`
- NOT: `{"type": "user_turn", "text": "..."}`

**Status:** ✅ Fixed in `refinement_loop/elevenlabs_client.py`

---

#### 2. **Agent Response Not Being Captured**
**Symptom:** WebSocket connects but agent responses are empty or come back as "Unknown"
**Cause:** The `_receive_agent_response` function may not be properly handling response events
**Fix Applied:**
- Improved message type handling (agent_response, agent_response_correction, audio)
- Better timeout logic (wait for multiple frames to ensure full response)
- Proper fallback chain: agent_response → correction stream → audio alignment

**Status:** ✅ Fixed in `refinement_loop/elevenlabs_client.py` (lines 118-215)

---

#### 3. **Agent Not Configured for Text Mode**
**Symptom:** Agent works fine in the ElevenLabs UI but doesn't respond over WebSocket
**Diagnosis Steps:**
1. Run the diagnostic tool:
   ```bash
   python diagnose_elevenlabs.py
   ```
2. Check each test result:
   - ✅ Configuration Check — API key and agent ID are set
   - ✅ Agent Health Check — agent responds to REST API
   - ✅ Prompt Retrieval — system prompt is retrieved successfully
   - ✅ Single-turn Conversation — test with one message
   - ✅ Multi-turn Conversation — test with multiple turns

3. If tests fail, check:
   - ElevenLabs dashboard → Agent → Conversation Config
   - Ensure "Conversation Mode" is not restricted to audio-only
   - Verify the agent is in "Deployed" state

---

#### 4. **WebSocket Connection Timeouts**
**Symptom:** Conversation starts but times out waiting for agent response
**Diagnosis:**
- Check your network latency to `api.elevenlabs.io`
- ElevenLabs may be slow under heavy load
- Diagnostic tool will show exact timeout patterns

**Current Settings:**
- Connection timeout: 30 seconds
- Per-turn timeout: 25 seconds (with 30-second fallback)
- You can adjust in `refinement_loop/config.py`

---

#### 5. **Missing Agent System Prompt**
**Symptom:** Agent responds but with "Unknown" or generic responses
**Cause:** The system prompt was not pushed to ElevenLabs
**Fix:**
1. Check `prompts/system_prompt.txt` exists and has content
2. Manually push the prompt:
   ```bash
   python -c "
   import asyncio
   from refinement_loop.elevenlabs_client import push_prompt
   
   prompt = open('prompts/system_prompt.txt').read()
   asyncio.run(push_prompt(prompt))
   print('Prompt pushed!')
   "
   ```
3. Wait 5-10 seconds for ElevenLabs to process
4. Test with `diagnose_elevenlabs.py` again

---

### Testing Flow

**Step 1: Verify Connection & Prompt**
```bash
python diagnose_elevenlabs.py
```
Wait for all 5 tests to pass before proceeding.

**Step 2: Test Text Mode (Optional)**
```bash
python test_text_mode.py
```
This will send a simple message and show the raw response structure.

**Step 3: Run a Single Scenario**
```bash
python -c "
import asyncio
from refinement_loop.simulator import simulate
from refinement_loop.scenarios import SCENARIOS

async def test():
    scenario = SCENARIOS[0]  # first scenario
    prompt = open('prompts/system_prompt.txt').read()
    transcript = await simulate(scenario, prompt)
    print(f'Turns captured: {len(transcript.turns)}')
    for turn in transcript.turns:
        role = 'CUSTOMER' if turn.role == 'customer' else 'AGENT'
        print(f'{role}: {turn.content[:80]}...')

asyncio.run(test())
"
```

**Step 4: Run Full Loop**
```bash
python -c "
import asyncio
from refinement_loop.loop import RefinementLoop

async def run():
    loop = RefinementLoop(scenario_ids=['book_next_available'])
    summary = await loop.run()
    print(f'Iterations: {len(summary.iterations)}')
    print(f'Reason: {summary. terminated_reason}')

asyncio.run(run())
"
```

---

### Debug Logging

**Enable verbose logging:**
```bash
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)

import asyncio
from refinement_loop.simulator import simulate
from refinement_loop.scenarios import SCENARIOS

async def test():
    scenario = SCENARIOS[0]
    prompt = open('prompts/system_prompt.txt').read()
    transcript = await simulate(scenario, prompt)

asyncio.run(test())
" 2>&1 | tee debug.log
```

This will show every WebSocket message received and sent.

---

### Common Issues & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| Wrong message format | Agent ignores text | Use `user_turn` with nesting: `{"type": "user_turn", "user_turn": {"text": "..."}}` |
| Missing prompt | Agent says "Unknown" | Push prompt to ElevenLabs: `asyncio.run(push_prompt(...))` |
| Timeout too short | Conversation cuts off | Increase timeout in `config.py`: `CONVERSATION_MAX_TIMEOUT = 40` |
| Rate limiter | Random failures | Diagnostic tool shows if this is issue; increase delay between turns |
| Agent offline | "Cannot connect" error | Check ElevenLabs dashboard—agent must be "Deployed" |

---

### Key Code Changes Made

1. **`elevenlabs_client.py` → `_receive_agent_response()`**
   - Better handling of multi-frame responses
   - Waits up to 5 empty frames before assuming response is complete
   - Proper fallback: agent_response → correction stream → audio alignment

2. **`elevenlabs_client.py` → `run_conversation()`**
   - Improved logging shows exactly what's happening each turn
   - Handles the case where agent sends empty response
   - Better error messages to help diagnose issues

3. **`test_text_mode.py`**
   - Fixed message format from `"text"` to `"user_turn": {"text": ...}`

---

### Next Steps

1. **Run diagnostic:** `python diagnose_elevenlabs.py`
2. **If all tests pass:** Run the full loop: `python -m refinement_loop.loop`
3. **If tests fail:** Post the error output here for specific troubleshooting

The diagnostic tool will tell you exactly which part is broken so we can target the fix.
