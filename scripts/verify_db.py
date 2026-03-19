#!/usr/bin/env python
"""
Verify the TechMellon database contents.

Run this script to check that the database was properly initialized.
Usage:
    python verify_db.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.db.database import get_conn

if __name__ == "__main__":
    print("📊 Verifying TechMellon database...\n")
    
    try:
        with get_conn() as conn:
            # Check tables exist
            tables_cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in tables_cursor.fetchall()]
            print(f"✅ Tables found: {', '.join(tables)}\n")
            
            # Count flights
            flights = conn.execute("SELECT COUNT(*) FROM flights").fetchone()
            print(f"✈️  Flights: {flights[0]}")
            
            # Count bookings
            bookings = conn.execute("SELECT COUNT(*) FROM bookings").fetchone()
            print(f"📝 Bookings: {bookings[0]}")
            
            # Show sample flights
            print("\n🌍 Sample flights (first 3):")
            sample = conn.execute("""
                SELECT id, origin, destination, departure_dt, price_gbp, seats_total - seats_booked as available
                FROM flights
                LIMIT 3
            """).fetchall()
            for row in sample:
                print(f"   {row[0]}: {row[1]} → {row[2]} | {row[3]} | £{row[4]} | {row[5]} seats available")
            
            # Show sample bookings
            print("\n📋 Sample bookings (first 3):")
            sample = conn.execute("""
                SELECT ref, passenger_name, status, total_paid_gbp
                FROM bookings
                LIMIT 3
            """).fetchall()
            for row in sample:
                print(f"   {row[0]}: {row[1]} | {row[2]} | £{row[3]}")
            
            print("\n✅ Database is healthy and ready to use!")
            
    except Exception as e:
        print(f"❌ Error verifying database: {e}")
        sys.exit(1)
