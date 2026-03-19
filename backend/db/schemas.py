"""
Pydantic request/response schemas for the FastAPI backend.
Used in route handlers for validation and serialization.
"""

from pydantic import BaseModel
from typing import Optional


# ── Flight schemas ────────────────────────────────────────────────────────────

class FlightOut(BaseModel):
    """Flight response model."""
    id: str
    origin: str
    destination: str
    departure_dt: str
    arrival_dt: str
    duration_min: int
    aircraft: str
    seat_class: str
    price_gbp: float
    seats_available: int
    status: str = "on_time"


class FlightSearchParams(BaseModel):
    """Flight search parameters."""
    destination: Optional[str] = None
    date: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    seat_class: Optional[str] = None


class FlightStatusOut(BaseModel):
    """Flight status response."""
    flight_id: str
    departure_dt: str
    status: str
    gate: Optional[str] = None
    delay_minutes: int = 0


# ── Booking schemas ───────────────────────────────────────────────────────────

class BookingCreateRequest(BaseModel):
    """Request body for creating a booking."""
    flight_id: str
    passenger_name: str
    seat_preference: Optional[str] = None
    fare_type: str = "standard"


class BookingOut(BaseModel):
    """Booking response model."""
    ref: str
    flight_id: str
    passenger_name: str
    seat_number: Optional[str] = None
    seat_preference: Optional[str] = None
    total_paid_gbp: float
    status: str
    created_at: str
    fare_type: str = "standard"
    flight: Optional[FlightOut] = None
    extras: list["ExtraOut"] = []
    assistance: list["AssistanceOut"] = []


class BookingRescheduleRequest(BaseModel):
    """Request body for rescheduling a booking."""
    new_flight_id: str


# ── Extras schemas ────────────────────────────────────────────────────────────

class ExtraAddRequest(BaseModel):
    """Request body for adding baggage/extras to a booking."""
    item_type: str  # extra_bag, pram, sports_equipment, oversized
    description: Optional[str] = None


class ExtraOut(BaseModel):
    """Extra item response model."""
    id: int
    booking_ref: str
    item_type: str
    description: Optional[str] = None
    fee_gbp: float


# ── Assistance schemas ────────────────────────────────────────────────────────

class AssistanceRequest(BaseModel):
    """Request body for special assistance."""
    assistance_code: str  # WCHR, WCHS, WCHC, BLND, DEAF, etc.
    notes: Optional[str] = None


class AssistanceOut(BaseModel):
    """Assistance response model."""
    id: int
    booking_ref: str
    assistance_code: str
    notes: Optional[str] = None
    confirmed: bool = True


BookingOut.model_rebuild()
