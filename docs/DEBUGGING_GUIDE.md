# DEBUGGING THE REFINEMENT LOOP

This guide helps you debug issues with the refinement loop, especially:
- Conversations only producing 1 turn
- Agent not responding
- Evaluation failing
- Missing logs

---

## Quick Start: Test Sequence

Run each script in order. Stop if any fails — that's your problem.

### 1. **Diagnostic Check** (5 seconds)
Verifies ElevenLabs configuration and connectivity.

```bash
python diagnose_elevenlabs.py
```

**Output:** Check `logs/diagnostic.log`

**Success indicators:**
- ✓ All environment variables set
- ✓ Agent exists on ElevenLabs
- ✓ WebSocket connects
- ✓ Agent responds to "Hello"

**If it fails:**
- Not set: Set `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID` in `.env`
- Agent not found: Verify agent ID in ElevenLabs dashboard
- Agent not responding: Check if agent is published/enabled in ElevenLabs

---

### 2. **Debug Test** (2-3 minutes)
Tests the full refinement loop on ONE scenario.

```bash
python test_loop_debug.py
```

**Output:** Check `logs/debug_test.log`

**What it tests:**
1. Customer script generation (Gemini)
2. Agent health check (ElevenLabs)
3. Full conversation (5-12 turns expected)
4. Transcript evaluation
5. Log file generation

**Success indicators:**
```
✓ Generated X customer utterances
✓ Agent is healthy and responding
✓ Conversation completed (turns: Y)
  Turn 1 [CUSTOMER]: ...
  Turn 1 [AGENT]: ...
  Turn 2 [CUSTOMER]: ...
  Turn 2 [AGENT]: ...
  ...
✓ ALL TESTS PASSED
```

**If conversation only has 1-2 turns:**
- Agent may be timing out (check logs for `⏱️ Agent response timeout`)
- Agent may be returning empty responses (check logs for `Agent returned empty response`)
- Network latency issue (ElevenLabs may be slow)

**If evaluation fails:**
- Empty transcript (no turns captured)
- Evaluator can't parse the conversation

---

### 3. **Full Loop** (5-20 minutes)
Runs the actual refinement loop with all 10 scenarios.

```bash
# Option A: Via UI (recommended for observation)
python start_loop.py
# Then open http://localhost:8000

# Option B: Standalone CLI
python -m refinement_loop.loop

# Option C: With custom thresholds
MAX_ITERATIONS=2 PASS_THRESHOLD=7.0 python start_loop.py
```

**Output:** Check `logs/`
- `loop_debug_YYYYMMDD_HHMMSS.log` — full debug log
- `run_YYYYMMDD_HHMMSS.json` — structured results (scores, changes, etc.)

---

## Common Issues & Fixes

### Issue: "Only 1 turn captured in conversation"

**Symptoms:**
```
✓ Generated 6 customer utterances
✗ Conversation completed (turns: 2)  # Only customer + agent
```

**Root causes:**

1. **Agent timeout after first response**
   - Look in debug log for: `⏱️ Agent response timeout for turn`
   - **Fix:** Increase timeout in `elevenlabs_client.py` line ~355
   ```python
   agent_text = await asyncio.wait_for(
       _receive_agent_response(ws), timeout=40.0  # was 25.0
   )
   ```

2. **Agent returns empty response**
   - Look for: `Agent returned empty response`
   - **Fix:** Check if agent's system prompt makes sense
     - Run `cat prompts/system_prompt.txt` and verify it exists
     - Check ElevenLabs agent dashboard for the prompt

3. **Agent says "goodbye" after turn 1**
   - Expected behavior — agent is following end-call instructions
   - This is OK — the scenario will be re-run in next iteration with updated prompt

4. **WebSocket drops unexpectedly**
   - Look for: `Failed to send user turn` or `Connection reset`
   - **Fix:** Network issue or ElevenLabs server issue
     - Try again (transient)
     - Check ElevenLabs status page

---

### Issue: "Agent not responding"

**Symptoms:**
```
Waiting for agent response (timeout: 25s)...
⏱️ Agent response timeout for turn 1 (waiting 30s more)
❌ Agent failed to respond on turn 1 (30s timeout exceeded)
```

**Causes:**

1. **Agent ID is invalid or agent doesn't exist**
   ```bash
   python diagnose_elevenlabs.py
   # Should show: ✗ Agent not found
   ```
   **Fix:** Set correct `ELEVENLABS_AGENT_ID` in `.env`

2. **Agent is not published**
   - Go to ElevenLabs dashboard
   - Check agent status (should be "active" or "ready")
   - If "draft", publish it first

3. **API key is invalid**
   ```bash
   python diagnose_elevenlabs.py
   # Should show: ✗ Unauthorized (invalid API key?)
   ```
   **Fix:** Set correct `ELEVENLABS_API_KEY` in `.env`

4. **ElevenLabs is experiencing issues**
   - Check [ElevenLabs status page](https://status.elevenlabs.io)
   - Try again after a few minutes

---

### Issue: "GOOGLE_API_KEY not set"

**Symptoms:**
```
⚠️  WARNING: GOOGLE_API_KEY not set — loop will run in DEMO MODE (simplified)
```

**Fix:**
```bash
export GOOGLE_API_KEY=<your-gemini-api-key>
# Or add to .env:
# GOOGLE_API_KEY=...
```

The loop can run in demo mode but customer simulations will be generic.

---

### Issue: "No changes needed" after evaluation

**Symptoms:**
Loop runs but shows "NO CHANGES" in UI or log.

**Causes:**

1. **All scenarios already pass (score ≥ 8.0)**
   - This is success! Loop will terminate with "passed"

2. **Evaluator thinks all failures are "code" not "prompt"**
   - Fixer won't generate code patches without context
   - Check the root_cause field in logs

---

## Viewing Detailed Logs

### During run:
```bash
# Terminal 1: Start the loop
python start_loop.py

# Terminal 2: Watch debug log in real-time
tail -f logs/loop_debug_*.log
```

### After run:
```bash
# View structured results (JSON)
cat logs/run_*.json | jq .

# View debug log
cat logs/loop_debug_*.log | less

# View all scenario evaluations
cat logs/run_*.json | jq '.iterations[].evaluations[]'
```

---

## Log File Locations

| File | Purpose | Format |
|------|---------|--------|
| `logs/diagnostic.log` | ElevenLabs config check | Plain text |
| `logs/debug_test.log` | Single scenario test | Plain text |
| `logs/loop_debug_YYYYMMDD_HHMMSS.log` | Full loop execution | Plain text (DEBUG level) |
| `logs/run_YYYYMMDD_HHMMSS.json` | Structured results | JSON (for UI + analysis) |

---

## Environment Setup

Create `.env` file in the project root:

```bash
# Required
ELEVENLABS_API_KEY=<your-key>
ELEVENLABS_AGENT_ID=<your-agent-id>

# Required for evaluation
GOOGLE_API_KEY=<your-gemini-key>

# Optional
MAX_ITERATIONS=5
PASS_THRESHOLD=8.0
MAX_CONVERSATION_TURNS=12
SIMULATION_DELAY_SECONDS=13
```

Then source it:
```bash
source .env
# or manually:
export $(cat .env | xargs)
```

---

## Example: Full Debug Session

```bash
# 1. Check config
python diagnose_elevenlabs.py
# ✓ All checks pass

# 2. Test one scenario
python test_loop_debug.py
# ✓ ALL TESTS PASSED

# 3. Run full loop
python start_loop.py
# (Or if API not running: python -m refinement_loop.loop)

# 4. Monitor
tail -f logs/loop_debug_*.log

# 5. Analyze results
cat logs/run_*.json | jq '.score_improvement'
```

---

## Need More Help?

1. **Check the debug log first:**
   ```bash
   cat logs/loop_debug_*.log | grep -i error
   ```

2. **Post relevant log section in error report**

3. **Include:**
   - The error/warning message
   - Relevant section of debug log (100 lines around error)
   - Output of `python diagnose_elevenlabs.py`
