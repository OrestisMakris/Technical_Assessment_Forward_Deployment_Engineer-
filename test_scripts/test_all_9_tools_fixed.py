import httpx
import json
import sqlite3

# Setup
BASE_URL = 'http://localhost:8000'
WEBHOOK_URL = f'{BASE_URL}/webhook/elevenlabs'
DB_PATH = 'techmellon.db'

print("=" * 80)
print("COMPREHENSIVE 9-TOOL WEBHOOK TEST + DB CROSS-REFERENCE")
print("=" * 80)
print()

# Utility to query DB
def query_db(sql):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        print(f"DB ERROR: {e}")
        return []

# Track results
tests_passed = 0
tests_failed = 0
booking_ref = None
flight_id_to_book = None

print("📊 DATABASE STATE BEFORE TESTS:")
print("-" * 80)
flights = query_db("SELECT COUNT(*) as cnt FROM flights")
bookings = query_db("SELECT COUNT(*) as cnt FROM bookings")
print(f"Total flights in DB: {flights[0]['cnt'] if flights else 0}")
print(f"Total bookings in DB: {bookings[0]['cnt'] if bookings else 0}")

# Sample flight
sample = query_db("SELECT id, origin, destination, price_gbp FROM flights LIMIT 1")
if sample:
    f = sample[0]
    print(f"Sample flight: {f['id']} ({f['origin']} → {f['destination']}, £{f['price_gbp']})")
print()

def test_tool(num, name, params, desc=""):
    """Test a tool and return response data"""
    global tests_passed, tests_failed
    
    print(f"\n{'='*80}")
    print(f"TEST {num}/9: {name}")
    if desc:
        print(f"Desc: {desc}")
    print(f"Params: {json.dumps(params)}")
    print("-" * 80)
    
    try:
        response = httpx.post(
            WEBHOOK_URL,
            json={'tool_name': name, 'parameters': params},
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status 200 | Response type: {type(data).__name__}")
            if isinstance(data, list):
                print(f"   Returned {len(data)} item(s)")
                if data:
                    print(f"   Sample: {str(data[0])[:100]}")
            elif isinstance(data, dict):
                print(f"   Keys: {list(data.keys())}")
                print(f"   Content: {str(data)[:100]}")
            tests_passed += 1
            return data, True
        else:
            print(f"❌ Status {response.status_code}")
            print(f"   Response: {response.text[:100]}")
            tests_failed += 1
            return None, False
    except Exception as e:
        print(f"❌ Exception: {str(e)[:80]}")
        tests_failed += 1
        return None, False

# ============================================================================
# TEST 1: Search Flights
# ============================================================================
data1, ok1 = test_tool(
    1, 'search_flights',
    {'destination': 'London', 'date': '2026-03-25'},
    'Find flights to London'
)

if ok1 and isinstance(data1, list) and data1:
    flight_id_to_book = data1[0].get('flight_id')
    print(f"\n✅ CROSS-REF: Got flight {flight_id_to_book}")
    
    # Verify in DB
    db_check = query_db(f"SELECT id FROM flights WHERE id = '{flight_id_to_book}'")
    if db_check:
        print(f"✅ Confirmed in DB: flight exists")
    else:
        print(f"⚠️ Not found in DB by that ID")

# ============================================================================
# TEST 2: Get Policy
# ============================================================================
data2, ok2 = test_tool(
    2, 'get_policy',
    {'topic': 'baggage-policy'},
    'Retrieve baggage policy'
)

# ============================================================================
# TEST 3: Get Flight Status
# ============================================================================
data3, ok3 = test_tool(
    3, 'get_flight_status',
    {'flight_id': 'LHR001'},
    'Check flight LHR001 status'
)

if ok3:
    db_check = query_db("SELECT id, status FROM flights WHERE id = 'LHR001'")
    if db_check:
        print(f"\n✅ CROSS-REF: LHR001 status in DB = {db_check[0]['status']}")

# ============================================================================
# TEST 4: Book Flight
# ============================================================================
if flight_id_to_book is None:
    # Fallback to any flight
    fallback = query_db("SELECT id FROM flights LIMIT 1")
    flight_id_to_book = fallback[0]['id'] if fallback else 'LHR001'

data4, ok4 = test_tool(
    4, 'book_flight',
    {
        'flight_id': flight_id_to_book,
        'passenger_name': 'Alice Smith',
        'seat_preference': 'window',
        'fare_type': 'economy'
    },
    f'Book flight {flight_id_to_book}'
)

if ok4 and isinstance(data4, dict):
    booking_ref = data4.get('booking_ref')
    if booking_ref:
        print(f"\n✅ Got booking ref: {booking_ref}")
        
        # Verify in DB
        db_check = query_db(f"SELECT ref FROM bookings WHERE ref = '{booking_ref}'")
        if db_check:
            print(f"✅ CROSS-REF: Booking created and verified in DB")

# ============================================================================
# TEST 5: Get Booking
# ============================================================================
if booking_ref:
    data5, ok5 = test_tool(
        5, 'get_booking',
        {'ref': booking_ref},
        f'Retrieve booking {booking_ref}'
    )
    if ok5:
        print(f"✅ CROSS-REF: Booking details returned from API")
else:
    # Try with existing booking from DB
    existing = query_db("SELECT ref FROM bookings LIMIT 1")
    if existing:
        test_ref = existing[0]['ref']
        print(f"\n(Using existing booking {test_ref} from DB)")
        data5, ok5 = test_tool(5, 'get_booking', {'ref': test_ref}, 'Get existing booking')
    else:
        print("\n⚠️ TEST 5 SKIPPED: No booking available")
        tests_failed += 1

# ============================================================================
# TEST 6: Add Extras
# ============================================================================
if booking_ref:
    data6, ok6 = test_tool(
        6, 'add_extras',
        {'ref': booking_ref, 'item_type': 'baggage', 'description': 'Extra checked baggage'},
        f'Add extra to {booking_ref}'
    )
    if ok6:
        db_check = query_db(f"SELECT id FROM booking_extras WHERE booking_ref = '{booking_ref}'")
        print(f"✅ CROSS-REF: {len(db_check)} extra(s) in DB")
else:
    print("\n⚠️ TEST 6 SKIPPED: No booking available")

# ============================================================================
# TEST 7: Add Assistance
# ============================================================================
if booking_ref:
    data7, ok7 = test_tool(
        7, 'add_assistance',
        {'ref': booking_ref, 'assistance_code': 'WCHR', 'notes': 'Wheelchair assistance'},
        f'Add assistance to {booking_ref}'
    )
    if ok7:
        db_check = query_db(f"SELECT id FROM assistance WHERE booking_ref = '{booking_ref}'")
        print(f"✅ CROSS-REF: {len(db_check)} assistance record(s) in DB")
else:
    print("\n⚠️ TEST 7 SKIPPED: No booking available")

# ============================================================================
# TEST 8: Reschedule Booking
# ============================================================================
if booking_ref and data1 and isinstance(data1, list):
    # Find a different flight
    other_flights = [f for f in data1 if f.get('flight_id') != flight_id_to_book]
    if other_flights:
        other_id = other_flights[0]['flight_id']
    else:
        other_id = 'LHR002'
    
    data8, ok8 = test_tool(
        8, 'reschedule_booking',
        {'ref': booking_ref, 'new_flight_id': other_id},
        f'Reschedule to {other_id}'
    )
    if ok8:
        print(f"✅ Rescheduling processed")
elif booking_ref:
    print("\n⚠️ TEST 8 SKIPPED: Need different flight for rescheduling")
else:
    print("\n⚠️ TEST 8 SKIPPED: No booking available")

# ============================================================================
# TEST 9: Cancel Booking
# ============================================================================
if booking_ref:
    data9, ok9 = test_tool(
        9, 'cancel_booking',
        {'ref': booking_ref},
        f'Cancel booking {booking_ref}'
    )
    if ok9:
        db_check = query_db(f"SELECT status FROM bookings WHERE ref = '{booking_ref}'")
        if db_check:
            print(f"✅ CROSS-REF: Booking status = {db_check[0]['status']}")
else:
    print("\n⚠️ TEST 9 SKIPPED: No booking available")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)
print(f"\n✅ Passed: {tests_passed}")
print(f"❌ Failed: {tests_failed}")

print("\n📊 DATABASE STATE AFTER TESTS:")
print("-" * 80)
final_flights = query_db("SELECT COUNT(*) as cnt FROM flights")
final_bookings = query_db("SELECT COUNT(*) as cnt FROM bookings")
final_extras = query_db("SELECT COUNT(*) as cnt FROM booking_extras")
final_assist = query_db("SELECT COUNT(*) as cnt FROM assistance")

print(f"Total flights: {final_flights[0]['cnt'] if final_flights else 0}")
print(f"Total bookings: {final_bookings[0]['cnt'] if final_bookings else 0}")
print(f"Total extras: {final_extras[0]['cnt'] if final_extras else 0}")
print(f"Total assistance: {final_assist[0]['cnt'] if final_assist else 0}")

print("\n✅ All tests completed")
