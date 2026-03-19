# TechMellon Airlines — Voice AI Refinement Loop

An autonomous evaluation and self-correction system for an ElevenLabs voice agent handling airline customer service.

---

## How to run

### 1. Clone and install

```bash
git clone <your-repo>
cd techmellon-fde
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export ELEVENLABS_API_KEY=...
export ELEVENLABS_AGENT_ID=...     # from ElevenLabs dashboard
```

If `ELEVENLABS_AGENT_ID` is not set, the system falls back to using Claude directly as the agent (useful for local development without ElevenLabs credentials).

### 3. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`. Docs at `/docs`.

### 4. Open the observation UI

Navigate to `http://localhost:8000` (static file served from `backend/static/index.html`).

### 5. Start the loop

Click **Start loop** in the UI, or via API:

```bash
curl -X POST http://localhost:8000/loop/start
```

To run a subset of scenarios:

```bash
curl -X POST "http://localhost:8000/loop/start" \
  -H "Content-Type: application/json" \
  -d '["book_next_available", "cancel_refund"]'
```

### 6. Adjust thresholds (for the walkthrough)

```bash
MAX_ITERATIONS=3 PASS_THRESHOLD=7.0 uvicorn backend.main:app --reload
```

Or via CLI directly (bypasses the API):

```bash
python -m refinement_loop.loop --max-iterations 3 --pass-threshold 7.0
```

---

## Architecture

```
refinement_loop/
  loop.py             Main orchestrator — iterate, terminate, broadcast SSE
  simulator.py        LLM plays the customer; generates utterance list upfront
  evaluator.py        Scores transcripts 1–10 per criterion, classifies root cause
  fixer.py            Rewrites system prompt or patches Python functions via AST
  elevenlabs_client.py  WS text-mode conversation + prompt push via REST API
  scenarios.py        10 customer scenarios with success criteria
  models.py           Dataclasses: Transcript, EvaluationResult, Fix, RunSummary
  config.py           All configurable constants (thresholds, models, paths)
  sse_bridge.py       Fan-out SSE queue connecting loop to FastAPI stream

backend/
  main.py             FastAPI app — mounts all routers, /loop/* endpoints
  db/database.py      SQLite schema, seed (35 flights over 7 days, 5 fixed bookings)
  db/schemas.py       Pydantic request/response models
  routes/flights.py   GET /flights/search, GET /flights/{id}/status
  routes/bookings.py  POST/GET/PUT/DELETE /bookings, PATCH /extras, PATCH /assistance
  routes/knowledge.py GET /knowledge/*, POST /webhook/elevenlabs dispatcher
  knowledge/policies.json  Pet, baggage, check-in, cancellation, assistance policies
  static/index.html   Observation UI (no build step, vanilla JS + SSE)
```

---

## APIs and tools used

| Tool | Purpose |
|---|---|
| ElevenLabs Conversational AI | Voice agent + text-mode WebSocket conversation |
| ElevenLabs REST API | Read/write system prompt (`PATCH /v1/convai/agents/{id}`) |
| Anthropic Claude (claude-sonnet-4-5) | Customer simulator, evaluator, fixer |
| FastAPI + SQLite | Booking API, persistence |
| Server-sent events | Real-time loop → UI communication |

---

## Tradeoffs and decisions

### Pre-generated customer utterances
The customer LLM writes its full script upfront rather than reacting turn-by-turn. **Tradeoff:** faster, cheaper, reproducible — but the customer can't adapt to surprising agent responses. A reactive mode is sketched in `simulator.py`. For an assessment covering 10 scenarios per iteration this felt like the right call.

### Function-level code patching (not diffs)
The fixer asks the LLM to return a complete replacement function, then uses Python's `ast` module to find and splice it in. **Tradeoff:** more reliable than applying a unified diff (LLMs often generate slightly malformed diffs), but can't do multi-function refactors. The assessment brief explicitly says "targeted, file-level patches to specific functions are sufficient."

### Evaluation batching
All 10 scenarios run concurrently (semaphore of 3) then are evaluated sequentially. Failures are batched into a single prompt-fix call. **Tradeoff:** one coherent prompt rewrite > many conflicting micro-patches.

### SQLite over Postgres
SQLite with WAL mode handles the low-concurrency load of this assessment fine. Switching to Postgres is a one-line DSN change. The schema avoids SQLite-specific syntax.

### SSE over WebSockets for the UI
SSE is strictly simpler for a one-way server-push stream. The loop only needs to push events to the browser; no browser-to-server messages needed. SSE is also easier to debug (plain text in DevTools).

---

## What I would improve for production

1. **Reactive simulation** — customer LLM reacts to each agent reply for higher-fidelity testing
2. **Parallel evaluation** — run evaluations concurrently to halve iteration time
3. **Prompt version control** — store every prompt revision in a database with scores attached
4. **Richer code patching** — use tree-sitter for language-aware multi-function patches
5. **Regression guard** — before pushing a new prompt, re-run all previously passing scenarios to detect regressions
6. **Auth on `/loop/start`** — currently open; needs API key header in production
7. **Postgres + Alembic** — for multi-instance deployments

---

## Log file format

Each run writes a structured JSON log to `logs/run_YYYYMMDD_HHMMSS.json`:

```json
{
  "terminated_reason": "passed | max_iterations",
  "total_iterations": 3,
  "score_improvement": 2.4,
  "initial_average_score": 5.8,
  "final_average_score": 8.2,
  "initial_prompt": "...",
  "final_prompt": "...",
  "iterations": [
    {
      "iteration": 1,
      "average_score": 5.8,
      "all_passed": false,
      "evaluations": [
        {
          "scenario_id": "book_next_available",
          "overall_score": 6.5,
          "root_cause": "prompt",
          "scores": [...]
        }
      ],
      "fixes": [
        {
          "type": "prompt",
          "description": "Rewrote system prompt to address 4 failing scenarios.",
          "diff": "--- a/system_prompt.txt\n+++ b/system_prompt.txt\n..."
        }
      ]
    }
  ]
}
```
