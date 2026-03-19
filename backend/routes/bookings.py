"""
Booking CRUD endpoints.

All write operations persist to SQLite. Bookings made by one caller
are immediately visible to the next (no in-memory state).
"""

from __future__ import annotations

import datetime
import random
import string
from typing import Optional

from fastapi import APIRouter, HTTPException

from backend.db.database import get_conn
from backend.db.schemas import (
    AssistanceOut,
    AssistanceRequest,
    BookingCreateRequest,
    BookingOut,
    BookingRescheduleRequest,
    ExtraAddRequest,
    ExtraOut,
    FlightOut,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])

# Extra item fees in GBP
EXTRA_FEES: dict[str, float] = {
    "extra_bag": 35.00,
    "pram": 20.00,
    "sports_equipment": 60.00,
    "oversized": 75.00,
}

# Seat maps — very simplified
SEAT_POOLS = {
    "window": ["12A", "14A", "18A", "22A", "30A", "34A"],
    "aisle": ["12C", "14C", "18C", "22C", "30C", "34C"],
    "extra_legroom": ["1A", "1C", "2A", "2C", "11A", "11C"],
}


def _generate_ref() -> str:
    suffix = "".join(random.choices(string.digits, k=4))
    return f"TM-{suffix}"


def _row_to_booking(row, conn) -> BookingOut:
    flight_row = conn.execute(
        "SELECT * FROM flights WHERE id = ?", (row["flight_id"],)
    ).fetchone()

    extras_rows = conn.execute(
        "SELECT * FROM booking_extras WHERE booking_ref = ?", (row["ref"],)
    ).fetchall()
    assistance_rows = conn.execute(
        "SELECT * FROM assistance WHERE booking_ref = ?", (row["ref"],)
    ).fetchall()

    flight_out = None
    if flight_row:
        flight_out = FlightOut(
            id=flight_row["id"],
            origin=flight_row["origin"],
            destination=flight_row["destination"],
            departure_dt=flight_row["departure_dt"],
            arrival_dt=flight_row["arrival_dt"],
            duration_min=flight_row["duration_min"],
            aircraft=flight_row["aircraft"],
            seat_class=flight_row["seat_class"],
            price_gbp=flight_row["price_gbp"],
            seats_available=flight_row["seats_total"] - flight_row["seats_booked"],
            status=flight_row["status"],
        )

    return BookingOut(
        ref=row["ref"],
        flight_id=row["flight_id"],
        passenger_name=row["passenger_name"],
        seat_preference=row["seat_preference"],
        seat_number=row["seat_number"],
        fare_type=row["fare_type"],
        status=row["status"],
        total_paid_gbp=row["total_paid_gbp"],
        created_at=row["created_at"],
        flight=flight_out,
        extras=[
            ExtraOut(
                id=e["id"],
                item_type=e["item_type"],
                description=e["description"],
                fee_gbp=e["fee_gbp"],
            )
            for e in extras_rows
        ],
        assistance=[
            AssistanceOut(
                id=a["id"],
                assistance_code=a["assistance_code"],
                notes=a["notes"],
                confirmed=bool(a["confirmed"]),
            )
            for a in assistance_rows
        ],
    )


# ── GET /bookings/{ref} ───────────────────────────────────────────────────────

@router.get("/{ref}", response_model=BookingOut)
def get_booking(ref: str):
    """Retrieve a booking by reference number."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Booking {ref} not found.")
        return _row_to_booking(row, conn)


# ── POST /bookings ────────────────────────────────────────────────────────────

@router.post("", response_model=BookingOut, status_code=201)
def create_booking(body: BookingCreateRequest):
    """
    Book a flight. Prevents double bookings by checking seat availability
    inside a transaction before committing.
    """
    now = datetime.datetime.utcnow().isoformat() + "Z"

    with get_conn() as conn:
        flight = conn.execute(
            "SELECT * FROM flights WHERE id = ?", (body.flight_id,)
        ).fetchone()

        if not flight:
            raise HTTPException(status_code=404, detail=f"Flight {body.flight_id} not found.")
        if flight["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="This flight has been cancelled.")
        if flight["seats_booked"] >= flight["seats_total"]:
            raise HTTPException(status_code=409, detail="No seats available on this flight.")

        # Assign a seat
        seat_number = None
        if body.seat_preference and body.seat_preference in SEAT_POOLS:
            taken = {
                r["seat_number"]
                for r in conn.execute(
                    "SELECT seat_number FROM bookings WHERE flight_id = ?", (body.flight_id,)
                ).fetchall()
                if r["seat_number"]
            }
            available = [s for s in SEAT_POOLS[body.seat_preference] if s not in taken]
            seat_number = available[0] if available else None

        ref = _generate_ref()
        # Ensure uniqueness
        while conn.execute("SELECT 1 FROM bookings WHERE ref = ?", (ref,)).fetchone():
            ref = _generate_ref()

        conn.execute(
            """INSERT INTO bookings
               (ref, flight_id, passenger_name, seat_preference, seat_number,
                fare_type, status, total_paid_gbp, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                ref, body.flight_id, body.passenger_name,
                body.seat_preference, seat_number,
                body.fare_type, "confirmed", flight["price_gbp"], now,
            ),
        )
        conn.execute(
            "UPDATE flights SET seats_booked = seats_booked + 1 WHERE id = ?",
            (body.flight_id,),
        )

        row = conn.execute("SELECT * FROM bookings WHERE ref = ?", (ref,)).fetchone()
        return _row_to_booking(row, conn)


# ── PUT /bookings/{ref} — reschedule ──────────────────────────────────────────

@router.put("/{ref}", response_model=BookingOut)
def reschedule_booking(ref: str, body: BookingRescheduleRequest):
    """Move an existing booking to a different flight."""
    with get_conn() as conn:
        booking = conn.execute(
            "SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)
        ).fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail=f"Booking {ref} not found.")
        if booking["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="Cannot reschedule a cancelled booking.")

        new_flight = conn.execute(
            "SELECT * FROM flights WHERE id = ?", (body.new_flight_id,)
        ).fetchone()
        if not new_flight:
            raise HTTPException(status_code=404, detail=f"Flight {body.new_flight_id} not found.")
        if new_flight["seats_booked"] >= new_flight["seats_total"]:
            raise HTTPException(status_code=409, detail="No seats available on the new flight.")

        old_flight_id = booking["flight_id"]

        conn.execute(
            "UPDATE bookings SET flight_id = ?, total_paid_gbp = ? WHERE ref = ?",
            (body.new_flight_id, new_flight["price_gbp"], ref.upper()),
        )
        conn.execute(
            "UPDATE flights SET seats_booked = seats_booked - 1 WHERE id = ?",
            (old_flight_id,),
        )
        conn.execute(
            "UPDATE flights SET seats_booked = seats_booked + 1 WHERE id = ?",
            (body.new_flight_id,),
        )

        row = conn.execute("SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)).fetchone()
        return _row_to_booking(row, conn)


# ── DELETE /bookings/{ref} — cancel ──────────────────────────────────────────

@router.delete("/{ref}")
def cancel_booking(ref: str):
    """
    Cancel a booking and compute refund.
    Flexible fares: 100% refund.
    Standard fares: no refund (credit only, not modelled here).
    """
    with get_conn() as conn:
        booking = conn.execute(
            "SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)
        ).fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail=f"Booking {ref} not found.")
        if booking["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="Booking is already cancelled.")

        refund_amount = booking["total_paid_gbp"] if booking["fare_type"] == "flexible" else 0.0
        refund_timeline = "5–7 business days" if refund_amount > 0 else "No refund applicable"

        conn.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE ref = ?", (ref.upper(),)
        )
        conn.execute(
            "UPDATE flights SET seats_booked = MAX(0, seats_booked - 1) WHERE id = ?",
            (booking["flight_id"],),
        )

    return {
        "ref": ref.upper(),
        "status": "cancelled",
        "refund_amount_gbp": refund_amount,
        "refund_timeline": refund_timeline,
        "fare_type": booking["fare_type"],
    }


# ── PATCH /bookings/{ref}/extras ──────────────────────────────────────────────

@router.patch("/{ref}/extras", response_model=BookingOut)
def add_extras(ref: str, body: ExtraAddRequest):
    """Add an extra bag or special item to an existing booking."""
    with get_conn() as conn:
        booking = conn.execute(
            "SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)
        ).fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail=f"Booking {ref} not found.")
        if booking["status"] == "cancelled":
            raise HTTPException(status_code=409, detail="Cannot add extras to a cancelled booking.")

        fee = EXTRA_FEES.get(body.item_type.lower(), 35.00)
        conn.execute(
            """INSERT INTO booking_extras (booking_ref, item_type, description, fee_gbp)
               VALUES (?,?,?,?)""",
            (ref.upper(), body.item_type.lower(), body.description, fee),
        )
        conn.execute(
            "UPDATE bookings SET total_paid_gbp = total_paid_gbp + ? WHERE ref = ?",
            (fee, ref.upper()),
        )

        row = conn.execute("SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)).fetchone()
        return _row_to_booking(row, conn)


# ── PATCH /bookings/{ref}/assistance ─────────────────────────────────────────

@router.patch("/{ref}/assistance", response_model=BookingOut)
def add_assistance(ref: str, body: AssistanceRequest):
    """
    Add a special assistance request.

    Valid codes:
      WCHR — wheelchair to/from aircraft door
      WCHS — wheelchair up/down steps
      WCHC — wheelchair full assistance, carried to seat
      BLND — assistance for visually impaired passengers
      DEAF — assistance for hearing impaired passengers
    """
    valid_codes = {"WCHR", "WCHS", "WCHC", "BLND", "DEAF"}
    code = body.assistance_code.upper()
    if code not in valid_codes:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid assistance code '{code}'. Valid: {', '.join(sorted(valid_codes))}",
        )

    with get_conn() as conn:
        booking = conn.execute(
            "SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)
        ).fetchone()
        if not booking:
            raise HTTPException(status_code=404, detail=f"Booking {ref} not found.")

        conn.execute(
            """INSERT INTO assistance (booking_ref, assistance_code, notes, confirmed)
               VALUES (?,?,?,1)""",
            (ref.upper(), code, body.notes),
        )

        row = conn.execute("SELECT * FROM bookings WHERE ref = ?", (ref.upper(),)).fetchone()
        return _row_to_booking(row, conn)
