#!/usr/bin/env python
"""
Requirement audit for project scope:
1) Knowledge Base
2) Flight Database
3) Booking APIs and webhooks

Run with:
  .venv\Scripts\python.exe test_requirements_core.py

Requires backend running on http://localhost:8000.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).parent))
from backend.db.database import get_conn

BASE = "http://localhost:8000"
WEBHOOK = f"{BASE}/webhook/elevenlabs"


@dataclass
class Check:
    name: str
    ok: bool
    details: str


results: list[Check] = []


def record(name: str, ok: bool, details: str) -> None:
    results.append(Check(name=name, ok=ok, details=details))


class SimpleResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self._payload}")


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None) -> SimpleResponse:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(url, data=data, headers=headers, method=method)
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return SimpleResponse(resp.status, parsed)
    except HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        parsed = json.loads(body) if body else {"error": str(exc)}
        return SimpleResponse(exc.code, parsed)


def req_get(path: str) -> SimpleResponse:
    return _http_json("GET", f"{BASE}{path}")


def req_post(path: str, payload: dict[str, Any]) -> SimpleResponse:
    return _http_json("POST", f"{BASE}{path}", payload)


def webhook(tool: str, params: dict[str, Any]) -> Any:
    r = req_post("/webhook/elevenlabs", {"tool_name": tool, "parameters": params})
    r.raise_for_status()
    body = r.json()
    return body.get("result")


def check_knowledge_base() -> None:
    required = {
        "pet": "/knowledge/pet-policy",
        "baggage": "/knowledge/baggage-policy",
        "assistance": "/knowledge/assistance-policy",
        "checkin": "/knowledge/checkin-policy",
        "cancellation": "/knowledge/cancellation-policy",
    }
    for key, path in required.items():
        r = req_get(path)
        ok = r.status_code == 200 and isinstance(r.json(), dict) and len(r.json()) > 0
        record(
            f"knowledge.{key}",
            ok,
            f"status={r.status_code}, keys={list(r.json().keys())[:5] if r.status_code == 200 else 'n/a'}",
        )



def check_flight_database() -> None:
    with get_conn() as conn:
        flights = conn.execute(
            "SELECT id, destination, departure_dt, seat_class, price_gbp FROM flights"
        ).fetchall()

    # single-week window check
    dep_dates = [dt.date.fromisoformat(row["departure_dt"][:10]) for row in flights]
    span_days = (max(dep_dates) - min(dep_dates)).days if dep_dates else 0
    record("db.single_week_window", span_days <= 6, f"span_days={span_days}")

    destinations = sorted({row["destination"] for row in flights})
    record("db.multiple_destinations", len(destinations) >= 5, f"count={len(destinations)}, values={destinations}")

    classes = sorted({row["seat_class"] for row in flights})
    record("db.multiple_seat_classes", len(classes) >= 2, f"count={len(classes)}, values={classes}")

    prices = [float(row["price_gbp"]) for row in flights]
    tier_ok = (max(prices) - min(prices)) >= 100
    record("db.pricing_tiers", tier_ok, f"min={min(prices):.2f}, max={max(prices):.2f}")



def check_booking_apis_and_webhooks() -> None:
    # Search by destination
    tokyo = webhook("search_flights", {"destination": "Tokyo"})
    ok_tokyo = isinstance(tokyo, list) and len(tokyo) > 0 and all("Tokyo" in f.get("destination", "") for f in tokyo)
    record("api.search_by_destination", ok_tokyo, f"count={len(tokyo) if isinstance(tokyo, list) else 'n/a'}")

    # Search by date
    if isinstance(tokyo, list) and tokyo:
        date_value = tokyo[0]["departure_dt"][:10]
        by_date = webhook("search_flights", {"destination": "Tokyo", "date": date_value})
        ok_date = isinstance(by_date, list) and len(by_date) > 0 and all(f["departure_dt"].startswith(date_value) for f in by_date)
        record("api.search_by_date", ok_date, f"date={date_value}, count={len(by_date) if isinstance(by_date, list) else 'n/a'}")
    else:
        record("api.search_by_date", False, "precondition failed: no Tokyo flights")

    # Search by price requirement check (this API does not expose max_price currently)
    # We test behavior via webhook payload; if unsupported, result is not constrained.
    all_paris = webhook("search_flights", {"destination": "Paris"})
    cheap_paris = webhook("search_flights", {"destination": "Paris", "max_price": 85})
    if isinstance(all_paris, list) and isinstance(cheap_paris, list) and all_paris and cheap_paris:
        max_returned = max(float(f["price_gbp"]) for f in cheap_paris)
        constrained = max_returned <= 85
        record("api.search_by_price", constrained, f"requested_max=85, max_returned={max_returned}")
    else:
        record("api.search_by_price", False, "could not evaluate price filtering")

    # Book flight and ensure persistence via separate retrieval
    tokyo_id = tokyo[0]["id"] if isinstance(tokyo, list) and tokyo else "TM-FL-001"
    booking = webhook(
        "book_flight",
        {
            "flight_id": tokyo_id,
            "passenger_name": "Requirement Audit",
            "seat_preference": "window",
        },
    )
    ref = booking.get("ref") if isinstance(booking, dict) else None
    persisted = webhook("get_booking", {"ref": ref}) if ref else {"error": "missing ref"}
    ok_persist = isinstance(persisted, dict) and persisted.get("ref") == ref
    record("api.book_and_persist", ok_persist, f"ref={ref}")

    # Prevent double booking / full-flight booking check
    # Force a flight to full in DB then verify API rejects booking with 409-style error body.
    with get_conn() as conn:
        target = conn.execute("SELECT id, seats_total FROM flights WHERE destination='Dublin' ORDER BY departure_dt LIMIT 1").fetchone()
        conn.execute("UPDATE flights SET seats_booked = seats_total WHERE id = ?", (target["id"],))
    full_attempt = req_post(
        "/bookings",
        {
            "flight_id": target["id"],
            "passenger_name": "Should Fail",
            "seat_preference": "aisle",
            "fare_type": "standard",
        },
    )
    full_rejected = full_attempt.status_code == 409
    record("api.prevent_booking_when_full", full_rejected, f"status={full_attempt.status_code}, flight={target['id']}")

    # Add extras
    add_extras = webhook("add_extras", {"ref": ref, "item_type": "extra_bag", "description": "23kg bag"})
    extras_ok = isinstance(add_extras, dict) and len(add_extras.get("extras", [])) > 0
    record("api.add_baggage_or_special_item", extras_ok, f"extras_count={len(add_extras.get('extras', [])) if isinstance(add_extras, dict) else 'n/a'}")

    # Reschedule
    paris = webhook("search_flights", {"destination": "Paris"})
    new_flight = paris[0]["id"] if isinstance(paris, list) and paris else None
    rs = webhook("reschedule_booking", {"ref": ref, "new_flight_id": new_flight}) if new_flight else {"error": "no flight"}
    rs_ok = isinstance(rs, dict) and rs.get("flight_id") == new_flight
    record("api.reschedule_booking", rs_ok, f"new_flight={new_flight}")

    # Cancel
    cancelled = webhook("cancel_booking", {"ref": ref})
    cancel_ok = isinstance(cancelled, dict) and cancelled.get("status") == "cancelled"
    record("api.cancel_booking", cancel_ok, f"status={cancelled.get('status') if isinstance(cancelled, dict) else 'n/a'}")



def main() -> int:
    print("=" * 90)
    print("REQUIREMENT AUDIT: Knowledge Base, Flight DB, Booking APIs/Webhooks")
    print("=" * 90)

    check_knowledge_base()
    check_flight_database()
    check_booking_apis_and_webhooks()

    passed = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]

    print("\nRESULTS")
    print("-" * 90)
    for r in results:
        status = "PASS" if r.ok else "FAIL"
        print(f"[{status}] {r.name}: {r.details}")

    print("\nSUMMARY")
    print("-" * 90)
    print(f"Passed: {len(passed)}")
    print(f"Failed: {len(failed)}")

    if failed:
        print("\nFAILED CHECKS")
        print("-" * 90)
        for f in failed:
            print(f"- {f.name}: {f.details}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
