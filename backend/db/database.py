"""
database.py — SQLite schema, connection management, and seed data.

All tables are created on first run. The seed function is idempotent:
it only inserts flights if the flights table is empty.

Schema overview
---------------
flights       — static schedule of available departures (read-only after seed)
bookings      — one row per booking; references a flight
booking_extras — bags / special items attached to a booking
assistance    — special assistance requests attached to a booking
"""

from __future__ import annotations

import datetime
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

DB_PATH = Path(os.getenv("DB_PATH", "techmellon.db"))


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ────────────────────────────────────────────────────────────────────

DDL = """
CREATE TABLE IF NOT EXISTS flights (
    id              TEXT PRIMARY KEY,
    origin          TEXT NOT NULL,
    destination     TEXT NOT NULL,
    departure_dt    TEXT NOT NULL,   -- ISO-8601 UTC
    arrival_dt      TEXT NOT NULL,
    duration_min    INTEGER NOT NULL,
    aircraft        TEXT NOT NULL,
    seat_class      TEXT NOT NULL,   -- economy / business / first
    price_gbp       REAL NOT NULL,
    seats_total     INTEGER NOT NULL,
    seats_booked    INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'on_time'  -- on_time / delayed / cancelled
);

CREATE TABLE IF NOT EXISTS bookings (
    ref             TEXT PRIMARY KEY,
    flight_id       TEXT NOT NULL REFERENCES flights(id),
    passenger_name  TEXT NOT NULL,
    seat_preference TEXT,            -- window / aisle / extra_legroom / null
    seat_number     TEXT,
    fare_type       TEXT NOT NULL DEFAULT 'standard',  -- standard / flexible
    status          TEXT NOT NULL DEFAULT 'confirmed', -- confirmed / cancelled
    total_paid_gbp  REAL NOT NULL,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (flight_id) REFERENCES flights(id)
);

CREATE TABLE IF NOT EXISTS booking_extras (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_ref     TEXT NOT NULL REFERENCES bookings(ref),
    item_type       TEXT NOT NULL,   -- extra_bag / pram / sports_equipment / oversized
    description     TEXT,
    fee_gbp         REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS assistance (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_ref     TEXT NOT NULL REFERENCES bookings(ref),
    assistance_code TEXT NOT NULL,   -- WCHR / WCHS / WCHC / BLND / DEAF / etc.
    notes           TEXT,
    confirmed       INTEGER NOT NULL DEFAULT 1
);
"""


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(DDL)
    seed_flights()


# ── Seed data — one week of flights ──────────────────────────────────────────

def seed_flights() -> None:
    with get_conn() as conn:
        existing = conn.execute("SELECT COUNT(*) FROM flights").fetchone()[0]
        if existing > 0:
            return

    # Base date: "today" so tests always have upcoming flights
    today = datetime.date.today()

    # Helper
    def dt(day_offset: int, hour: int, minute: int = 0) -> str:
        d = today + datetime.timedelta(days=day_offset)
        return f"{d.isoformat()}T{hour:02d}:{minute:02d}:00"

    flights = [
        # ── London → Tokyo ────────────────────────────────────────────────────
        ("TM-FL-001", "London", "Tokyo",     dt(0,  8),  dt(0, 21), 780, "B777", "economy",  620.00, 180),
        ("TM-FL-002", "London", "Tokyo",     dt(1, 10),  dt(1, 23), 780, "B777", "economy",  595.00, 180),
        ("TM-FL-003", "London", "Tokyo",     dt(2, 22),  dt(3, 11), 780, "A350", "business", 2100.00, 40),
        ("TM-FL-004", "London", "Tokyo",     dt(3,  9),  dt(3, 22), 780, "B777", "economy",  610.00, 180),
        # ── London → Paris ────────────────────────────────────────────────────
        ("TM-FL-010", "London", "Paris",     dt(0,  7),  dt(0,  8, 15), 75, "A320", "economy",   89.00, 150),
        ("TM-FL-011", "London", "Paris",     dt(0, 12),  dt(0, 13, 15), 75, "A320", "economy",   79.00, 150),
        ("TM-FL-012", "London", "Paris",     dt(1,  9),  dt(1, 10, 15), 75, "A319", "economy",   95.00, 140),
        ("TM-FL-013", "London", "Paris",     dt(2, 16),  dt(2, 17, 15), 75, "A320", "economy",   82.00, 150),
        ("TM-FL-014", "London", "Paris",     dt(4,  8),  dt(4,  9, 15), 75, "A320", "economy",   92.00, 150),
        # ── London → Barcelona ────────────────────────────────────────────────
        ("TM-FL-020", "London", "Barcelona", dt(0,  6),  dt(0,  9),    180, "A320", "economy",  115.00, 160),
        ("TM-FL-021", "London", "Barcelona", dt(1, 13),  dt(1, 16),    180, "A320", "economy",  105.00, 160),
        ("TM-FL-022", "London", "Barcelona", dt(2,  8),  dt(2, 11),    180, "A320", "economy",  130.00, 160),
        ("TM-FL-023", "London", "Barcelona", dt(4, 18),  dt(4, 21),    180, "A321", "economy",  125.00, 175),
        ("TM-FL-024", "London", "Barcelona", dt(5, 10),  dt(5, 13),    180, "A320", "economy",  118.00, 160),
        ("TM-FL-025", "London", "Barcelona", dt(6,  7),  dt(6, 10),    180, "A320", "economy",  109.00, 160),
        # ── London → New York ─────────────────────────────────────────────────
        ("TM-FL-030", "London", "New York",  dt(0,  9),  dt(0, 17),    480, "B787", "economy",  450.00, 200),
        ("TM-FL-031", "London", "New York",  dt(1, 11),  dt(1, 19),    480, "B787", "economy",  420.00, 200),
        ("TM-FL-032", "London", "New York",  dt(2, 14),  dt(2, 22),    480, "B777", "business",1800.00,  50),
        ("TM-FL-033", "London", "New York",  dt(3, 10),  dt(3, 18),    480, "B787", "economy",  435.00, 200),
        ("TM-FL-034", "London", "New York",  dt(5,  8),  dt(5, 16),    480, "B787", "economy",  398.00, 200),
        # ── London → Rome ─────────────────────────────────────────────────────
        ("TM-FL-040", "London", "Rome",      dt(0,  7),  dt(0,  9, 30), 150, "A319", "economy",  98.00, 140),
        ("TM-FL-041", "London", "Rome",      dt(1, 14),  dt(1, 16, 30), 150, "A320", "economy",  88.00, 150),
        ("TM-FL-042", "London", "Rome",      dt(3, 10),  dt(3, 12, 30), 150, "A320", "economy",  102.00, 150),
        ("TM-FL-043", "London", "Rome",      dt(5,  8),  dt(5, 10, 30), 150, "A319", "economy",   94.00, 140),
        # ── London → Dublin ───────────────────────────────────────────────────
        ("TM-FL-050", "London", "Dublin",    dt(0,  6),  dt(0,  7, 20),  80, "A319", "economy",   59.00, 140),
        ("TM-FL-051", "London", "Dublin",    dt(0,  9, 15), dt(0, 10, 35), 80, "A319", "economy", 65.00, 140),
        ("TM-FL-052", "London", "Dublin",    dt(1,  7),  dt(1,  8, 20),  80, "A320", "economy",   55.00, 150),
        ("TM-FL-053", "London", "Dublin",    dt(1,  9),  dt(1, 10, 20),  80, "A319", "economy",   62.00, 140),
        ("TM-FL-054", "London", "Dublin",    dt(2,  8),  dt(2,  9, 20),  80, "A319", "economy",   58.00, 140),
        # ── London → Lisbon ───────────────────────────────────────────────────
        ("TM-FL-060", "London", "Lisbon",    dt(0, 10),  dt(0, 12, 30), 150, "A320", "economy",  110.00, 160),
        ("TM-FL-061", "London", "Lisbon",    dt(2, 15),  dt(2, 17, 30), 150, "A320", "economy",  105.00, 160),
        ("TM-FL-062", "London", "Lisbon",    dt(4,  9),  dt(4, 11, 30), 150, "A321", "economy",  122.00, 175),
        ("TM-FL-063", "London", "Lisbon",    dt(6,  8),  dt(6, 10, 30), 150, "A320", "economy",  108.00, 160),
    ]

    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO flights
               (id, origin, destination, departure_dt, arrival_dt,
                duration_min, aircraft, seat_class, price_gbp, seats_total)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            flights,
        )

    # Seed the fixed bookings referenced by assessment scenarios
    _seed_fixed_bookings()


def _seed_fixed_bookings() -> None:
    """Pre-create the bookings referenced in assessment scenarios."""
    now = datetime.datetime.utcnow().isoformat() + "Z"

    with get_conn() as conn:
        # TM-4821 — Paris booking to be rescheduled
        paris_mon = conn.execute(
            "SELECT id FROM flights WHERE destination='Paris' ORDER BY departure_dt LIMIT 1"
        ).fetchone()
        if paris_mon:
            conn.execute(
                """INSERT OR IGNORE INTO bookings
                   (ref, flight_id, passenger_name, fare_type, status, total_paid_gbp, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("TM-4821", paris_mon["id"], "Sarah Mitchell", "standard", "confirmed", 89.00, now),
            )
            conn.execute(
                "UPDATE flights SET seats_booked = seats_booked + 1 WHERE id = ?",
                (paris_mon["id"],),
            )

        # TM-3301 — New York booking to be cancelled (flexible fare)
        ny_flight = conn.execute(
            "SELECT id FROM flights WHERE destination='New York' ORDER BY departure_dt LIMIT 1"
        ).fetchone()
        if ny_flight:
            conn.execute(
                """INSERT OR IGNORE INTO bookings
                   (ref, flight_id, passenger_name, fare_type, status, total_paid_gbp, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("TM-3301", ny_flight["id"], "Daniel Webb", "flexible", "confirmed", 450.00, now),
            )
            conn.execute(
                "UPDATE flights SET seats_booked = seats_booked + 1 WHERE id = ?",
                (ny_flight["id"],),
            )

        # TM-6610 — Rome booking to have extras added
        rome_flight = conn.execute(
            "SELECT id FROM flights WHERE destination='Rome' ORDER BY departure_dt LIMIT 1"
        ).fetchone()
        if rome_flight:
            conn.execute(
                """INSERT OR IGNORE INTO bookings
                   (ref, flight_id, passenger_name, fare_type, status, total_paid_gbp, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("TM-6610", rome_flight["id"], "Lucas Fontaine", "standard", "confirmed", 98.00, now),
            )
            conn.execute(
                "UPDATE flights SET seats_booked = seats_booked + 1 WHERE id = ?",
                (rome_flight["id"],),
            )

        # TM-2200 — Dublin booking for check-in/status enquiry
        dublin_flight = conn.execute(
            "SELECT id FROM flights WHERE destination='Dublin' AND id='TM-FL-051'"
        ).fetchone()
        if dublin_flight:
            conn.execute(
                """INSERT OR IGNORE INTO bookings
                   (ref, flight_id, passenger_name, fare_type, status, total_paid_gbp, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("TM-2200", dublin_flight["id"], "Aoife Murphy", "standard", "confirmed", 65.00, now),
            )
            conn.execute(
                "UPDATE flights SET seats_booked = seats_booked + 1 WHERE id = ?",
                (dublin_flight["id"],),
            )

        # TM-5540 — Lisbon booking needing wheelchair assistance
        lisbon_flight = conn.execute(
            "SELECT id FROM flights WHERE destination='Lisbon' ORDER BY departure_dt LIMIT 1"
        ).fetchone()
        if lisbon_flight:
            conn.execute(
                """INSERT OR IGNORE INTO bookings
                   (ref, flight_id, passenger_name, fare_type, status, total_paid_gbp, created_at)
                   VALUES (?,?,?,?,?,?,?)""",
                ("TM-5540", lisbon_flight["id"], "Carlos Mendes", "standard", "confirmed", 110.00, now),
            )
            conn.execute(
                "UPDATE flights SET seats_booked = seats_booked + 1 WHERE id = ?",
                (lisbon_flight["id"],),
            )
