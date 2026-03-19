"""Flight search and status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.db.database import get_conn
from backend.db.schemas import FlightOut, FlightSearchParams, FlightStatusOut

router = APIRouter(prefix="/flights", tags=["flights"])


def _row_to_flight(row) -> FlightOut:
    return FlightOut(
        id=row["id"],
        origin=row["origin"],
        destination=row["destination"],
        departure_dt=row["departure_dt"],
        arrival_dt=row["arrival_dt"],
        duration_min=row["duration_min"],
        aircraft=row["aircraft"],
        seat_class=row["seat_class"],
        price_gbp=row["price_gbp"],
        seats_available=row["seats_total"] - row["seats_booked"],
        status=row["status"],
    )


@router.get("/search", response_model=list[FlightOut])
def search_flights(
    destination: Optional[str] = Query(None),
    origin: Optional[str] = Query("London"),
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    min_price: Optional[float] = Query(None, description="Minimum price in GBP"),
    max_price: Optional[float] = Query(None, description="Maximum price in GBP"),
    cheapest: bool = Query(False, description="Return only the single cheapest flight"),
    seat_class: Optional[str] = Query(None),
):
    """
    Search available flights.
    At least one filter should be provided; returns all matching flights
    with at least one seat available, sorted by price ascending.
    """
    sql = """
        SELECT * FROM flights
        WHERE seats_booked < seats_total
          AND status != 'cancelled'
    """
    params: list = []

    if destination:
        sql += " AND LOWER(destination) LIKE LOWER(?)"
        params.append(f"%{destination}%")

    if origin:
        sql += " AND LOWER(origin) LIKE LOWER(?)"
        params.append(f"%{origin}%")

    if date:
        sql += " AND DATE(departure_dt) = ?"
        params.append(date)

    if seat_class:
        sql += " AND LOWER(seat_class) = LOWER(?)"
        params.append(seat_class)

    if min_price is not None:
        sql += " AND price_gbp >= ?"
        params.append(min_price)

    if max_price is not None:
        sql += " AND price_gbp <= ?"
        params.append(max_price)

    sql += " ORDER BY price_gbp ASC"

    if cheapest:
        sql += " LIMIT 1"

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No flights found matching the criteria.")

    return [_row_to_flight(r) for r in rows]


@router.get("/{flight_id}/status", response_model=FlightStatusOut)
def get_flight_status(flight_id: str):
    """Return current status of a specific flight."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM flights WHERE id = ?", (flight_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found.")

    # Simulate gate assignment for flights departing within 24h
    import datetime
    dep = datetime.datetime.fromisoformat(row["departure_dt"])
    now = datetime.datetime.utcnow()
    gate = None
    if (dep - now).total_seconds() < 86400:
        # Deterministic gate from flight ID
        gate_num = (hash(flight_id) % 30) + 1
        gate_letter = "ABCD"[hash(flight_id) % 4]
        gate = f"{gate_letter}{gate_num}"

    return FlightStatusOut(
        flight_id=row["id"],
        status=row["status"],
        departure_dt=row["departure_dt"],
        gate=gate,
        delay_minutes=0 if row["status"] == "on_time" else 45,
    )
