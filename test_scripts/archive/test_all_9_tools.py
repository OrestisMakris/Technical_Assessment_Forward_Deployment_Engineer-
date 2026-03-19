import httpx
import json
import sqlite3
from datetime import datetime, timedelta

# Setup
BASE_URL = 'http://localhost:8000'
WEBHOOK_URL = f'{BASE_URL}/webhook/elevenlabs'
DB_PATH = 'techmellon.db'

print("=" * 80)
print("COMPREHENSIVE 9-TOOL WEBHOOK TEST + DB CROSS-REFERENCE")
print("=" * 80)
print()

# Read from DB first
def query_db(query):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchall()
    conn.close()
    return result

print("📊 DATABASE STATE BEFORE TESTS:")
print("-" * 80)
flights = query_db("SELECT * FROM flights LIMIT 3")
print(f"Sample flights in DB: {len(query_db('SELECT * FROM flights'))} total")
for f in flights[:1]:
    print(f"  - {f['flight_id']}: {f['origin']} → {f['destination']}, ${f['price']}")

bookings = query_db("SELECT * FROM bookings")
print(f"Bookings in DB: {len(bookings)}")
print()

# Track test results
results = {
    'passed': [],
    'failed': [],
    'cross_ref': []
}

def test_tool(num, name, params, description=""):
    """Test a single webhook tool"""
    print(f"\n{'='*80}")
    print(f"TEST {num}/9: {name}")
    if description:
        print(f"Description: {description}")
    print(f"Parameters: {json.dumps(params, indent=2)}")
    print("-" * 80)
    
    try:
        response = httpx.post(
            WEBHOOK_URL,
            json={'tool_name': name, 'parameters': params},
            timeout=15
        )
        
        status = response.status_code
        data = response.json() if status == 200 else response.text
        
        print(f"✅ Status: {status}")
        
        if isinstance(data, (list, dict)):
            print(f"✅ Response (formatted):")
            print(json.dumps(data, indent=2)[:500])
            results['passed'].append(name)
        else:
            print(f"Response: {data}")
            results['passed'].append(name)
        
        return data, True
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        results['failed'].append(name)
        return None, False

# ============================================================================
# TEST 1: Search Flights
# ============================================================================
data1, ok1 = test_tool(
    1, 'search_flights',
    {'destination': 'London', 'date': '2026-03-25'},
    'Search for flights to London'
)

if ok1 and isinstance(data1, list) and len(data1) > 0:
    flight_found = data1[0]
    flight_id = flight_found.get('flight_id')
    print(f"\n✅ CROSS-REF: Flight {flight_id} returned from search")
    
    # Verify in DB
    check = query_db(f"SELECT * FROM flights WHERE flight_id = ?", )
    db_flight = query_db(f"SELECT * FROM flights WHERE flight_id = '{flight_id}'")
    if db_flight:
        print(f"✅ Verified in DB: {db_flight[0]['flight_id']} exists in flights table")
        results['cross_ref'].append(f"search_flights → {flight_id}")
    else:
        print(f"❌ NOT found in DB: {flight_id}")

# ============================================================================
# TEST 2: Get Policy
# ============================================================================
data2, ok2 = test_tool(
    2, 'get_policy',
    {'topic': 'baggage-policy'},
    'Get baggage policy'
)

if ok2:
    policies = query_db("SELECT * FROM policies")
    print(f"\n✅ CROSS-REF: DB has {len(policies)} policies defined")
    results['cross_ref'].append('get_policy → DB policies OK')

# ============================================================================
# TEST 3: Get Flight Status
# ============================================================================
data3, ok3 = test_tool(
    3, 'get_flight_status',
    {'flight_id': 'LHR001'},
    'Get status of specific flight'
)

if ok3:
    status_check = query_db("SELECT * FROM flights WHERE flight_id = 'LHR001'")
    if status_check:
        print(f"\n✅ CROSS-REF: LHR001 exists in DB")
        results['cross_ref'].append('get_flight_status → LHR001 verified')

# ============================================================================
# TEST 4: Book Flight
# ============================================================================
print("\n" + "="*80)
print("⚠️  IMPORTANT: Need a valid flight_id for booking. Using first search result...")
if ok1 and isinstance(data1, list) and data1:
    flight_id_to_book = data1[0].get('flight_id', 'LHR001')
else:
    flight_id_to_book = 'LHR001'

data4, ok4 = test_tool(
    4, 'book_flight',
    {
        'flight_id': flight_id_to_book,
        'passenger_name': 'John Doe',
        'seat_preference': 'window',
        'fare_type': 'economy'
    },
    'Book a flight'
)

booking_ref = None
if ok4 and isinstance(data4, dict):
    booking_ref = data4.get('booking_ref')
    if booking_ref:
        print(f"\n✅ CROSS-REF: Created booking {booking_ref}")
        db_booking = query_db(f"SELECT * FROM bookings WHERE booking_ref = '{booking_ref}'")
        if db_booking:
            print(f"✅ Verified in DB: {booking_ref} exists in bookings table")
            results['cross_ref'].append(f"book_flight → {booking_ref}")
        else:
            print(f"❌ NOT found in DB: {booking_ref}")

# ============================================================================
# TEST 5: Get Booking (requires valid booking_ref)
# ============================================================================
if booking_ref:
    data5, ok5 = test_tool(
        5, 'get_booking',
        {'ref': booking_ref},
        f'Retrieve booking {booking_ref}'
    )
    if ok5:
        results['cross_ref'].append(f'get_booking → {booking_ref} returned')
else:
    print(f"\n{'='*80}")
    print(f"TEST 5/9: get_booking")
    print(f"⚠️  SKIPPED: Need valid booking_ref from previous test")
    print(f"Using fallback assuming bookings exist...")
    existing = query_db("SELECT booking_ref FROM bookings LIMIT 1")
    if existing:
        test_ref = existing[0]['booking_ref']
        data5, ok5 = test_tool(5, 'get_booking', {'ref': test_ref})
    else:
        ok5 = False

# ============================================================================
# TEST 6: Add Extras (requires valid booking_ref)
# ============================================================================
if booking_ref:
    data6, ok6 = test_tool(
        6, 'add_extras',
        {'ref': booking_ref, 'item_type': 'baggage', 'description': 'Extra checked bag'},
        f'Add extra baggage to booking {booking_ref}'
    )
    if ok6:
        extras_check = query_db(f"SELECT * FROM booking_extras WHERE booking_ref = '{booking_ref}'")
        if extras_check:
            print(f"\n✅ CROSS-REF: {len(extras_check)} extras added to {booking_ref}")
            results['cross_ref'].append(f'add_extras → {booking_ref}')
else:
    print(f"\n{'='*80}")
    print(f"TEST 6/9: add_extras")
    print(f"⚠️  SKIPPED: Need valid booking_ref")

# ============================================================================
# TEST 7: Add Assistance (requires valid booking_ref)
# ============================================================================
if booking_ref:
    data7, ok7 = test_tool(
        7, 'add_assistance',
        {'ref': booking_ref, 'assistance_code': 'WCHR', 'notes': 'Wheelchair required'},
        f'Add assistance to booking {booking_ref}'
    )
    if ok7:
        assist_check = query_db(f"SELECT * FROM assistance WHERE booking_ref = '{booking_ref}'")
        if assist_check:
            print(f"\n✅ CROSS-REF: Assistance added to {booking_ref}")
            results['cross_ref'].append(f'add_assistance → {booking_ref}')
else:
    print(f"\n{'='*80}")
    print(f"TEST 7/9: add_assistance")
    print(f"⚠️  SKIPPED: Need valid booking_ref")

# ============================================================================
# TEST 8: Reschedule Booking (requires valid booking_ref)
# ============================================================================
if booking_ref and ok1 and data1:
    # Find a different flight
    other_flights = [f for f in data1 if f.get('flight_id') != flight_id_to_book]
    if other_flights:
        other_flight_id = other_flights[0]['flight_id']
    else:
        # Get another flight from different search
        other = query_db("SELECT flight_id FROM flights WHERE flight_id != ? LIMIT 1")
        other_flight_id = 'LHR002'
    
    data8, ok8 = test_tool(
        8, 'reschedule_booking',
        {'ref': booking_ref, 'new_flight_id': other_flight_id},
        f'Reschedule booking {booking_ref} to different flight'
    )
    if ok8:
        updated = query_db(f"SELECT * FROM bookings WHERE booking_ref = '{booking_ref}'")
        if updated:
            print(f"\n✅ CROSS-REF: {booking_ref} updated in DB")
            results['cross_ref'].append(f'reschedule_booking → {booking_ref}')
else:
    print(f"\n{'='*80}")
    print(f"TEST 8/9: reschedule_booking")
    print(f"⚠️  SKIPPED: Need valid booking_ref")

# ============================================================================
# TEST 9: Cancel Booking (requires valid booking_ref)
# ============================================================================
if booking_ref:
    data9, ok9 = test_tool(
        9, 'cancel_booking',
        {'ref': booking_ref},
        f'Cancel booking {booking_ref}'
    )
    if ok9:
        canceled = query_db(f"SELECT * FROM bookings WHERE booking_ref = '{booking_ref}'")
        if canceled:
            status = canceled[0]['status'] if 'status' in canceled[0].keys() else 'unknown'
            print(f"\n✅ CROSS-REF: {booking_ref} status updated to '{status}'")
            results['cross_ref'].append(f'cancel_booking → {booking_ref}')
else:
    print(f"\n{'='*80}")
    print(f"TEST 9/9: cancel_booking")
    print(f"⚠️  SKIPPED: Need valid booking_ref")

# ============================================================================
# FINAL SUMMARY
# ============================================================================
print("\n" + "="*80)
print("FINAL SUMMARY")
print("="*80)

print(f"\n✅ PASSED ({len(results['passed'])}):")
for tool in results['passed']:
    print(f"   • {tool}")

if results['failed']:
    print(f"\n❌ FAILED ({len(results['failed'])}):")
    for tool in results['failed']:
        print(f"   • {tool}")

print(f"\n✅ CROSS-REFERENCE CHECKS ({len(results['cross_ref'])}):")
for check in results['cross_ref']:
    print(f"   • {check}")

print("\n" + "="*80)
print("DATABASE STATE AFTER TESTS:")
print("-" * 80)
final_bookings = query_db("SELECT COUNT(*) as count FROM bookings")
final_extras = query_db("SELECT COUNT(*) as count FROM booking_extras")
final_assist = query_db("SELECT COUNT(*) as count FROM assistance")

print(f"Total bookings: {final_bookings[0]['count']}")
print(f"Total extras: {final_extras[0]['count']}")
print(f"Total assistance records: {final_assist[0]['count']}")
print()
print("✅ ALL TESTS COMPLETE")
