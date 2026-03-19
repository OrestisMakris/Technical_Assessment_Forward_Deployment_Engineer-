"""
Pydantic request/response schemas for the FastAPI backend.
Used in route handlers for validation and serialization.
"""

from pydantic import BaseModel
from typing import Optional


class FlightSearchRequest(BaseModel):
    destination: Optional[str] = None
    date: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    seat_class: Optional[str] = None


class FlightResponse(BaseModel):
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


class BookingRequest(BaseModel):
    flight_id: str
    passenger_name: str
    seat_preference: Optional[str] = None
    fare_type: str = "standard"


class BookingResponse(BaseModel):
    ref: str
    flight_id: str
    passenger_name: str
    seat_number: Optional[str]
    total_paid_gbp: float
    status: str
    created_at: str


class BaggageRequest(BaseModel):
    booking_ref: str
    item_type: str
    description: Optional[str] = None
    fee_gbp: float = 0.0


class AssistanceRequest(BaseModel):
    booking_ref: str
    assistance_code: str
    notes: Optional[str] = None


class PolicyQuery(BaseModel):
    policy_type: str  # "pet", "baggage", "assistance", "checkin", "cancellation"
    query: Optional[str] = None
