"""
knowledge.py — policy query endpoints AND the ElevenLabs webhook handler.

ElevenLabs calls webhooks during a conversation when the agent invokes a tool.
The webhook receives a JSON body with the tool name and parameters, and must
return a JSON response the agent reads aloud / uses to continue the call.

All booking + flight operations are routed through the same underlying
route handlers so the agent always gets consistent data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

POLICIES_FILE = Path(__file__).parent / "policies.json"
_policies: dict = {}


def _load_policies() -> dict:
    global _policies
    if not _policies:
        _policies = json.loads(POLICIES_FILE.read_text(encoding="utf-8"))
    return _policies


knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])
webhook_router = APIRouter(prefix="/webhook", tags=["webhook"])


# ── Knowledge endpoints ───────────────────────────────────────────────────────

@knowledge_router.get("/pet-policy")
def get_pet_policy():
    return _load_policies()["pet_policy"]

@knowledge_router.get("/baggage-policy")
def get_baggage_policy():
    return _load_policies()["baggage_policy"]

@knowledge_router.get("/checkin-policy")
def get_checkin_policy():
    return _load_policies()["checkin_policy"]

@knowledge_router.get("/cancellation-policy")
def get_cancellation_policy():
    return _load_policies()["cancellation_refund_policy"]

@knowledge_router.get("/assistance-policy")
def get_assistance_policy():
    return _load_policies()["special_assistance"]

@knowledge_router.get("/infant-child-policy")
def get_infant_child_policy():
    return _load_policies()["infant_and_child_policy"]

@knowledge_router.get("/seat-policy")
def get_seat_policy():
    return _load_policies()["seat_policy"]

@knowledge_router.get("/loyalty-program")
def get_loyalty_program():
    return _load_policies()["loyalty_program"]

@knowledge_router.get("/meals-onboard")
def get_meals_onboard():
    return _load_policies()["meal_and_onboard_policy"]

@knowledge_router.get("/travel-documents")
def get_travel_documents():
    return _load_policies()["travel_documents_policy"]

@knowledge_router.get("/disruption-policy")
def get_disruption_policy():
    return _load_policies()["flight_disruption_policy"]

@knowledge_router.get("/payment-policy")
def get_payment_policy():
    return _load_policies()["payment_policy"]

@knowledge_router.get("/group-booking")
def get_group_booking():
    return _load_policies()["group_booking_policy"]

@knowledge_router.get("/medical-fitness")
def get_medical_fitness():
    return _load_policies()["medical_fitness_policy"]

@knowledge_router.get("/environmental-policy")
def get_environmental_policy():
    return _load_policies()["environmental_policy"]


@knowledge_router.get("/{topic}")
def get_policy(topic: str):
    policies = _load_policies()
    key = topic.replace("-", "_")
    if key not in policies:
        raise HTTPException(
            status_code=404,
            detail=f"Policy '{topic}' not found. Available: {list(policies.keys())}",
        )
    return {"topic": key, "content": policies[key]}


# ── ElevenLabs webhook handler ────────────────────────────────────────────────
#
# ElevenLabs POSTs to this endpoint when the agent calls a tool.
# Body format:
#   {
#     "tool_name": "search_flights",
#     "tool_call_id": "...",
#     "parameters": { ... }
#   }
#
# We dispatch to the appropriate business logic and return:
#   { "result": <any JSON-serialisable value> }

def _infer_tool_from_params(params: dict) -> str | None:
    """
    Infer tool name from parameter keys when tool_name is not provided.
    Useful for ElevenLabs test tool which sends params directly.
    """
    if not params:
        return None

    param_keys = set(params.keys())
    
    # Tool signatures (parameter combinations)
    signatures = {
        "search_flights": {"destination", "date", "cheapest", "seat_class", "origin"},
        "book_flight": {"flight_id", "passenger_name", "seat_preference"},
        "get_booking": {"ref"},
        "get_flight_status": {"flight_id"},
        "cancel_booking": {"ref"},
        "reschedule_booking": {"ref", "new_flight_id"},
        "add_extras": {"ref", "item_type", "description"},
        "add_assistance": {"ref", "assistance_code", "notes"},
        "get_policy": {"topic"},
    }
    
    # Find tool with matching parameter set (best match by overlap)
    best_match = None
    best_score = 0
    
    for tool, expected_params in signatures.items():
        # Score based on overlap with expected parameters
        overlap = len(param_keys & expected_params)
        if overlap > best_score:
            best_score = overlap
            best_match = tool
    
    return best_match if best_score > 0 else None


@webhook_router.post("/elevenlabs")
async def elevenlabs_webhook(request: Request) -> JSONResponse:
    """
    Central dispatcher for all ElevenLabs tool calls.
    
    Receives tool invocations from the ElevenLabs Conversational AI agent,
    dispatches to the appropriate handler, and returns results wrapped in
    a standardized {"result": <data>} response format.
    
    CRITICAL PARAMETER NOTES:
    - Use 'ref' (not 'booking_ref') for booking operations
    - Use 'date' in YYYY-MM-DD format (not departure_date)
    - Use 'seat_class' (not travel_class): economy/business/first
    - Empty string parameters are cleaned to prevent SQL "match all" behavior
    
    RESPONSE FORMAT:
    All tool responses are wrapped in {"result": <handler_output>}
    - search_flights: {"result": [flights]}
    - Others: {"result": {object}}
    - Errors: {"result": {"error": "message"}}
    
    Payload formats accepted:
    1. {"tool_name": "...", "parameters": {...}}
    2. {"tool_call": {"tool_name": "...", "parameters": {...}}}
    3. {parameters at root with inferred tool_name}
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    # ElevenLabs can send tool_name in multiple ways:
    # 1. {"tool_name": "...", "parameters": {...}}
    # 2. {"tool_call": {"tool_name": "...", "parameters": {...}}}
    # 3. {parameters directly at root} - from ElevenLabs test tool
    tool_call = body.get("tool_call", {})
    tool_name: str = body.get("tool_name") or tool_call.get("tool_name", "")
    params: dict = body.get("parameters") or tool_call.get("parameters", {})
    
    # If params not found in standard locations, check if params are at root level
    if not params and not tool_name:
        # Try to infer from root-level keys (include all keys, even empty ones)
        params = {k: v for k, v in body.items() if k not in ["tool_name", "tool_call", "parameters"]}
        tool_name = _infer_tool_from_params(params) or ""
        logger.info("Inferred from root params: tool=%s, keys=%s", tool_name, list(params.keys()))

    # Filter out empty string parameters to avoid "match all" behavior in SQL LIKE queries
    params_cleaned = {k: v for k, v in params.items() if v not in ("", None)}
    
    logger.info("ElevenLabs webhook received: %s", body)
    logger.info("ElevenLabs webhook: tool=%s raw_params=%s cleaned_params=%s", tool_name, params, params_cleaned)

    handler = _TOOL_DISPATCH.get(tool_name)
    if handler is None:
        if not tool_name:
            logger.error("❌ Could not determine tool_name from payload.")
            logger.error("📖 Ensure tool_name is in payload or configure tools in ElevenLabs.")
            return JSONResponse({
                "result": "ERROR: Could not determine which tool to call. Please configure tools in ElevenLabs agent. See ELEVENLABS_AGENT_CONFIG.md."
            }, status_code=200)
        logger.warning("Unknown tool: %s", tool_name)
        return JSONResponse({"result": f"Tool '{tool_name}' is not available."}, status_code=200)

    try:
        result = await handler(params_cleaned)
        return JSONResponse({"result": result})
    except HTTPException as exc:
        return JSONResponse({"result": {"error": exc.detail}}, status_code=200)
    except Exception as exc:
        logger.exception("Webhook handler error for tool '%s'", tool_name)
        return JSONResponse({"result": {"error": str(exc)}}, status_code=200)


# ── Tool handlers ─────────────────────────────────────────────────────────────

async def _tool_search_flights(params: dict) -> Any:
    """
    Search for flights by destination and date.
    
    Expected parameters:
      - destination: str (required) — e.g., "Tokyo", "New York"
      - date: str (required) — YYYY-MM-DD format, e.g., "2026-03-25"
      - origin: str (optional) — default "London"
      - seat_class: str (optional) — "economy", "business", or "first"
      - min_price: float (optional) — minimum price in £
      - max_price: float (optional) — maximum price in £
      - cheapest: bool (optional) — if True, sort by price ascending
    
    Returns: List of flight objects with fields:
      flight_id, origin, destination, departure_dt, arrival_dt, duration_min,
      aircraft, seat_class, price_gbp, seats_total, seats_available, status
    
    Response is wrapped in {"result": [flights]} by the webhook dispatcher.
    """
    from backend.routes.flights import search_flights
    return [f.model_dump() for f in search_flights(
        destination=params.get("destination"),
        origin=params.get("origin", "London"),
        date=params.get("date"),
        min_price=params.get("min_price"),
        max_price=params.get("max_price"),
        cheapest=params.get("cheapest", False),
        seat_class=params.get("seat_class"),
    )]


async def _tool_book_flight(params: dict) -> Any:
    """
    Book a flight for a passenger.
    
    Expected parameters:
      - flight_id: str (required) — e.g., "TM-FL-001"
      - passenger_name: str (required) — full name of passenger
      - seat_preference: str (optional) — "window", "aisle", "extra_legroom"
      - fare_type: str (optional) — "standard" or "flexible", default "standard"
    
    Returns: Booking object with fields:
      ref (booking reference), flight_id, passenger_name, seat_number,
      seat_preference, fare_type, status, total_paid_gbp, created_at
    
    Response wrapped in {"result": {booking}} by webhook dispatcher.
    """
    from backend.db.schemas import BookingCreateRequest
    from backend.routes.bookings import create_booking
    req = BookingCreateRequest(
        flight_id=params["flight_id"],
        passenger_name=params["passenger_name"],
        seat_preference=params.get("seat_preference"),
        fare_type=params.get("fare_type", "standard"),
    )
    booking = create_booking(req)
    return booking.model_dump()


async def _tool_get_booking(params: dict) -> Any:
    """
    Retrieve booking details by booking reference.
    
    Expected parameters:
      - ref: str (required) — booking reference, e.g., "TM-1234"
    
    Returns: Full booking object with:
      ref, flight_id, passenger_name, seat_number, seat_preference,
      fare_type, status, total_paid_gbp, created_at,
      flight (nested), extras[], assistance[]
    
    Response wrapped in {"result": {booking}} by webhook dispatcher.
    """
    from backend.routes.bookings import get_booking
    booking = get_booking(params["ref"])
    return booking.model_dump()


async def _tool_cancel_booking(params: dict) -> Any:
    """
    Cancel a booking and process refund.
    
    Expected parameters:
      - ref: str (required) — booking reference, e.g., "TM-1234"
    
    Returns: Cancellation result with fields:
      ref, status ("cancelled"), refund_amount_gbp, refund_timeline, fare_type
    
    Response wrapped in {"result": {cancellation}} by webhook dispatcher.
    """
    from backend.routes.bookings import cancel_booking
    return cancel_booking(params["ref"])


async def _tool_reschedule_booking(params: dict) -> Any:
    """
    Reschedule a booking to a different flight.
    
    Expected parameters:
      - ref: str (required) — booking reference, e.g., "TM-1234"
      - new_flight_id: str (required) — target flight ID, e.g., "TM-FL-002"
    
    Returns: Updated booking object with new flight_id and details.
    
    Response wrapped in {"result": {booking}} by webhook dispatcher.
    """
    from backend.db.schemas import BookingRescheduleRequest
    from backend.routes.bookings import reschedule_booking
    req = BookingRescheduleRequest(new_flight_id=params["new_flight_id"])
    booking = reschedule_booking(params["ref"], req)
    return booking.model_dump()


async def _tool_add_extras(params: dict) -> Any:
    """
    Add extra items (baggage, sports equipment, etc.) to a booking.
    
    Expected parameters:
      - ref: str (required) — booking reference, e.g., "TM-1234"
      - item_type: str (required) — type of item:
        "baggage", "pram", "sports_equipment", "oversized"
      - description: str (optional) — details about the item
    
    Returns: Updated booking with extras[] array.
    
    Response wrapped in {"result": {booking}} by webhook dispatcher.
    """
    from backend.db.schemas import ExtraAddRequest
    from backend.routes.bookings import add_extras
    req = ExtraAddRequest(
        item_type=params["item_type"],
        description=params.get("description"),
    )
    booking = add_extras(params["ref"], req)
    return booking.model_dump()


async def _tool_add_assistance(params: dict) -> Any:
    """
    Add special assistance request to a booking (mobility, deaf, blind, etc.).
    
    Expected parameters:
      - ref: str (required) — booking reference, e.g., "TM-1234"
      - assistance_code: str (required) — IATA assistance code:
        "WCHR" (wheelchair ramp), "WCHS" (wheelchair stairs),
        "WCHC" (wheelchair cabin), "BLND" (blind), "DEAF" (deaf)
      - notes: str (optional) — additional details
    
    Returns: Updated booking with assistance[] array.
    
    Response wrapped in {"result": {booking}} by webhook dispatcher.
    """
    from backend.db.schemas import AssistanceRequest
    from backend.routes.bookings import add_assistance
    req = AssistanceRequest(
        assistance_code=params["assistance_code"],
        notes=params.get("notes"),
    )
    booking = add_assistance(params["ref"], req)
    return booking.model_dump()


async def _tool_flight_status(params: dict) -> Any:
    """
    Get current status of a flight.
    
    Expected parameters:
      - flight_id: str (required) — e.g., "TM-FL-001"
    
    Returns: Flight status object with fields:
      flight_id, departure_dt, status (on_time/delayed/cancelled),
      gate, delay_minutes
    
    Response wrapped in {"result": {status}} by webhook dispatcher.
    """
    from backend.routes.flights import get_flight_status
    return get_flight_status(params["flight_id"]).model_dump()


async def _tool_get_policy(params: dict) -> Any:
    """
    Retrieve airline policy by topic.
    
    Expected parameters:
      - topic: str (required) — policy topic, e.g.:
        "baggage-policy", "cancellation-policy", "pet-policy",
        "seat-policy", "loyalty-program", "infant-child-policy",
        etc.
    
    Returns: Policy content as nested dict with detailed information.
    
    Response wrapped in {"result": {policy}} by webhook dispatcher.
    """
    topic = params.get("topic", "")
    policies = _load_policies()
    key = topic.replace("-", "_")
    return policies.get(key, {"error": f"Policy '{topic}' not found."})


_TOOL_DISPATCH = {
    "search_flights": _tool_search_flights,
    "book_flight": _tool_book_flight,
    "get_booking": _tool_get_booking,
    "cancel_booking": _tool_cancel_booking,
    "reschedule_booking": _tool_reschedule_booking,
    "add_extras": _tool_add_extras,
    "add_assistance": _tool_add_assistance,
    "get_flight_status": _tool_flight_status,
    "get_policy": _tool_get_policy,
}
