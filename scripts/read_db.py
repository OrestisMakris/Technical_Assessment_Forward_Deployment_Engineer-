#!/usr/bin/env python
"""Read database and show test data for all 9 tools."""
import sqlite3

conn = sqlite3.connect('techmellon.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("FLIGHTS - Sample Data")
print("=" * 80)
cursor.execute('SELECT * FROM flights LIMIT 10')
flights = cursor.fetchall()
for row in flights:
    print(f"ID: {row['id']:12} | {row['origin']:10} -> {row['destination']:10} | {row['departure_dt'][:10]} | {row['seat_class']:8} | £{row['price_gbp']:5} | Status: {row['status']}")

print("\n" + "=" * 80)
print("BOOKINGS - Sample Data")
print("=" * 80)
cursor.execute('SELECT * FROM bookings LIMIT 10')
bookings = cursor.fetchall()
for row in bookings:
    print(f"Ref: {row['booking_ref']:8} | Flight: {row['flight_id']:12} | Passenger: {row['passenger_name']:20} | Status: {row['booking_status']}")

print("\n" + "=" * 80)
print("POLICIES")
print("=" * 80)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for t in tables:
    print(f"  - {t[0]}")

conn.close()

# Show recommendations
print("\n" + "=" * 80)
print("TEST CASE RECOMMENDATIONS FOR EACH TOOL")
print("=" * 80)

conn = sqlite3.connect('techmellon.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute('SELECT DISTINCT destination FROM flights LIMIT 1')
dest = cursor.fetchone()['destination'] if cursor.fetchone() else 'Paris'

cursor.execute('SELECT * FROM flights LIMIT 1')
flight = cursor.fetchone()

cursor.execute('SELECT * FROM bookings LIMIT 1')
booking = cursor.fetchone()

cursor.execute('SELECT DISTINCT destination FROM flights ORDER BY RANDOM() LIMIT 1')
alt_dest = cursor.fetchone()['destination']

cursor.execute('SELECT DISTINCT flight_id FROM flights ORDER BY RANDOM() LIMIT 1')
alt_flight = cursor.fetchone()['id']

print(f"""
1. search_flights
   - destination: "{dest}"
   - date: "{flight['departure_dt'][:10]}" (or empty)
   - cheapest: true or false
   - seat_class: "{flight['seat_class']}"
   - origin: "{flight['origin']}"

2. book_flight
   - flight_id: "{flight['id']}"
   - passenger_name: "John Smith"
   - seat_preference: "window"

3. get_booking
   - ref: "{booking['booking_ref']}"

4. get_flight_status
   - flight_id: "{flight['id']}"

5. cancel_booking
   - ref: "{booking['booking_ref']}"

6. reschedule_booking
   - ref: "{booking['booking_ref']}"
   - new_flight_id: "{alt_flight}"

7. add_extras
   - ref: "{booking['booking_ref']}"
   - item_type: "extra_bag"
   - description: "Checked baggage"

8. add_assistance
   - ref: "{booking['booking_ref']}"
   - assistance_code: "WCHR"
   - notes: "Wheelchair assistance"

9. get_policy
   - topic: "baggage_policy" or "cancellation_refund_policy" or "pet_policy"
""")

conn.close()
