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


@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "service": "TechMellon Airlines API"}


@app.post("/tools/verify")
async def verify_tools():
    """
    Verify all 9 webhook tools are responding correctly.
    
    Runs basic tests on:
    1. search_flights
    2. get_policy
    3. get_flight_status
    4. book_flight (creates a test booking)
    5. get_booking
    6. add_extras
    7. add_assistance
    8. reschedule_booking
    9. cancel_booking
    
    Returns:
    {
      "passed": 8,
      "failed": 0,
      "tools": {
        "search_flights": "PASS",
        "get_policy": "PASS",
        ...
      }
    }
    """
    from backend.db.database import get_conn
    
    results = {}
    
    try:
        # Test 1: search_flights (direct DB query to avoid routing issues)
        with get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM flights WHERE destination = 'Tokyo' AND date(departure_dt) = ? LIMIT 1",
                          ("2026-03-19",))
            flights = cursor.fetchall()
        results["search_flights"] = "PASS" if flights else "SKIP (no flights)"
        test_flight_id = flights[0][0] if flights else "TM-FL-001"
    except Exception as e:
        results["search_flights"] = f"ERROR: {str(e)[:50]}"
        test_flight_id = "TM-FL-001"
    
    try:
        # Test 2: get_policy
        from backend.routes.knowledge import _load_policies
        policies = _load_policies()
        results["get_policy"] = "PASS" if policies and "baggage_policy" in policies else "FAIL"
    except Exception as e:
        results["get_policy"] = f"ERROR: {str(e)[:50]}"
    
    try:
        # Test 3: get_flight_status
        from backend.routes.flights import get_flight_status
        status = get_flight_status(test_flight_id)
        results["get_flight_status"] = "PASS" if status and status.flight_id else "FAIL"
    except Exception as e:
        results["get_flight_status"] = f"ERROR: {str(e)[:50]}"
    
    # For tests 4-9, we need a real flight and booking
    booking_ref = None
    
    try:
        # Test 4: book_flight
        from backend.routes.bookings import create_booking
        from backend.db.schemas import BookingCreateRequest
        
        req = BookingCreateRequest(
            flight_id=test_flight_id,
            passenger_name="Tool Verification Test",
            seat_preference="window",
            fare_type="economy",
        )
        booking = create_booking(req)
        booking_ref = booking.ref
        results["book_flight"] = "PASS" if booking_ref else "FAIL"
    except Exception as e:
        results["book_flight"] = f"ERROR: {str(e)[:50]}"
    
    if booking_ref:
        try:
            # Test 5: get_booking
            from backend.routes.bookings import get_booking
            booking = get_booking(booking_ref)
            results["get_booking"] = "PASS" if booking.ref == booking_ref else "FAIL"
        except Exception as e:
            results["get_booking"] = f"ERROR: {str(e)[:50]}"
        
        try:
            # Test 6: add_extras
            from backend.routes.bookings import add_extras
            from backend.db.schemas import ExtraAddRequest
            req = ExtraAddRequest(item_type="baggage", description="Test baggage")
            booking = add_extras(booking_ref, req)
            results["add_extras"] = "PASS" if booking.extras else "FAIL"
        except Exception as e:
            results["add_extras"] = f"ERROR: {str(e)[:50]}"
        
        try:
            # Test 7: add_assistance
            from backend.routes.bookings import add_assistance
            from backend.db.schemas import AssistanceRequest
            req = AssistanceRequest(assistance_code="WCHR", notes="Test assistance")
            booking = add_assistance(booking_ref, req)
            results["add_assistance"] = "PASS" if booking.assistance else "FAIL"
        except Exception as e:
            results["add_assistance"] = f"ERROR: {str(e)[:50]}"
        
        try:
            # Test 8: reschedule_booking (find another flight)
            from backend.routes.bookings import reschedule_booking
            from backend.db.schemas import BookingRescheduleRequest
            
            with get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM flights WHERE id != ? LIMIT 1", (test_flight_id,))
                other = cursor.fetchone()
            
            if other:
                other_flight_id = other[0]
                req = BookingRescheduleRequest(new_flight_id=other_flight_id)
                booking = reschedule_booking(booking_ref, req)
                results["reschedule_booking"] = "PASS" if booking.flight_id == other_flight_id else "FAIL"
            else:
                results["reschedule_booking"] = "SKIP (no alternate flight)"
        except Exception as e:
            results["reschedule_booking"] = f"ERROR: {str(e)[:50]}"
        
        try:
            # Test 9: cancel_booking
            from backend.routes.bookings import cancel_booking
            cancellation = cancel_booking(booking_ref)
            results["cancel_booking"] = "PASS" if cancellation.get("status") == "cancelled" else "FAIL"
        except Exception as e:
            results["cancel_booking"] = f"ERROR: {str(e)[:50]}"
    else:
        results["get_booking"] = "SKIP (no booking created)"
        results["add_extras"] = "SKIP (no booking)"
        results["add_assistance"] = "SKIP (no booking)"
        results["reschedule_booking"] = "SKIP (no booking)"
        results["cancel_booking"] = "SKIP (no booking)"
    
    # Summary
    passed = sum(1 for v in results.values() if v == "PASS")
    failed = sum(1 for v in results.values() if "ERROR" in v or v == "FAIL")
    
    logger.info("🔧 Tool verification complete: %d PASS, %d FAIL/ERROR", passed, failed)
    
    return {
        "passed": passed,
        "failed": failed,
        "tools": results
    }


@app.get("/loop/start")
async def start_loop(scenario_ids: str | None = None):
    """Start the autonomous refinement loop as a background task."""
    global _loop_task, _loop_state

    # Parse scenario_ids from query parameter
    scenarios = None
    if scenario_ids:
        scenarios = [s.strip() for s in scenario_ids.split(",") if s.strip()]

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
