"""
main.py — FastAPI application entry point.

Routes:
  /flights/*          flight search and status
  /bookings/*         booking CRUD
  /knowledge/*        policy queries
  /webhook/elevenlabs ElevenLabs tool call dispatcher
  /loop/start         start the refinement loop as a background task
  /loop/stream        SSE stream for the observation UI
  /loop/status        current loop state (for polling fallback)
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.db.database import init_db
from backend.routes.flights import router as flights_router
from backend.routes.bookings import router as bookings_router
from backend.routes.knowledge import knowledge_router, webhook_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialised.")
    yield


app = FastAPI(
    title="TechMellon Airlines API",
    version="1.0.0",
    description="Booking API + webhook handler for the ElevenLabs voice agent.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flights_router)
app.include_router(bookings_router)
app.include_router(knowledge_router)
app.include_router(webhook_router)


# ── Refinement loop control endpoints ────────────────────────────────────────

_loop_task: asyncio.Task | None = None
_loop_state = {"status": "idle", "iteration": 0}


@app.post("/loop/start")
async def start_loop(
    background_tasks: BackgroundTasks,
    scenarios: list[str] | None = None,
):
    """Start the autonomous refinement loop as a background task."""
    global _loop_task, _loop_state

    logger.info("🔴 START LOOP BUTTON CLICKED")
    logger.info("  Scenarios: %s", scenarios or "all")

    if _loop_task and not _loop_task.done():
        logger.warning("⚠️  Loop already running, rejecting start request")
        return JSONResponse({"status": "already_running"}, status_code=409)

    _loop_state = {"status": "running", "iteration": 0}

    from refinement_loop.sse_bridge import run_loop_background
    logger.info("✅ Creating background loop task...")
    _loop_task = asyncio.create_task(run_loop_background(scenario_ids=scenarios))
    logger.info("✅ Loop task created: %s", _loop_task)

    return {"status": "started"}


@app.get("/loop/status")
def loop_status():
    return {
        "status": "running" if (_loop_task and not _loop_task.done()) else "idle",
        **_loop_state,
    }


@app.get("/loop/stream")
async def loop_stream(request: Request):
    """
    Server-sent events stream for the observation UI.
    Connect with EventSource('/loop/stream').
    """
    from refinement_loop.sse_bridge import sse_manager

    async def generator():
        q = sse_manager.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15.0)
                    import json
                    event_name = event.get("event", "message")
                    data = json.dumps(event)
                    yield f"event: {event_name}\ndata: {data}\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            sse_manager.unsubscribe(q)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Serve static files (observer UI) ──────────────────────────────────────────

from pathlib import Path

static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
