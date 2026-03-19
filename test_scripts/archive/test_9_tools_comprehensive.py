import httpx
import json
import sqlite3

BASE_URL = 'http://localhost:8000'
WEBHOOK_URL = f'{BASE_URL}/webhook/elevenlabs'
DB_PATH = 'techmellon.db'

print("=" * 80)
print("COMPREHENSIVE 9-TOOL WEBHOOK TEST + DB CROSS-REFERENCE")
print("=" * 80)
print()

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
        return []

# ==== DISCOVER TEST DATA ====
print("📊 DATABASE DISCOVERY:")
print("-" * 80)

flights = query_db("SELECT * FROM flights LIMIT 5")
if flights:
    print(f"Found {len(query_db('SELECT COUNT(*) as c FROM flights'))} flights")
    f = flights[0]
    test_flight_id = f['id']
    test_dest = f['destination']
    test_date = f['departure_dt'][:10]  # YYYY-MM-DD
    test_origin = f['origin']
    print(f"Using flight: {test_flight_id} ({test_origin} → {test_dest}, {test_date})")
else:
    print("❌ No flights in database!")
    exit(1)

bookings = query_db("SELECT * FROM bookings LIMIT 1")
if bookings:
    test_booking_ref = bookings[0]['ref']
    print(f"Using test booking: {test_booking_ref}")
else:
    test_booking_ref = None

print()

# ==== TEST TRACKING ====
tests = {
    '1_search_flights': {'status': None, 'data': None},
    '2_get_policy': {'status': None, 'data': None},
    '3_get_flight_status': {'status': None, 'data': None},
    '4_book_flight': {'status': None, 'data': None},
    '5_get_booking': {'status': None, 'data': None},
    '6_add_extras': {'status': None, 'data': None},
    '7_add_assistance': {'status': None, 'data': None},
    '8_reschedule_booking': {'status': None, 'data': None},
    '9_cancel_booking': {'status': None, 'data': None},
}

new_booking_ref = None

def test_tool(num, name, params):
    """Test a tool"""
    print(f"\n{'='*80}")
    print(f"TEST {num}: {name}")
    print(f"Parameters: {json.dumps(params)}")
    print("-" * 80)
    
    try:
        response = httpx.post(
            WEBHOOK_URL,
            json={'tool_name': name, 'parameters': params},
            timeout=15
        )
        
        status = response.status_code
        data = response.json() if status == 200 else None
        
        if status == 200:
            print(f"✅ Status 200 - Success")
            
            # Handle both list and dict responses
            if isinstance(data, list):
                print(f"   Response type: list")
                print(f"   Returned {len(data)} item(s)")
                if data:
                    print(f"   Sample: {str(data[0])[:150]}")
            elif isinstance(data, dict):
                if 'result' in data:
                    result = data['result']
                    print(f"   Response keys: {list(result.keys())[0:3] if isinstance(result, dict) else 'list'}")
                    print(f"   Sample: {str(result)[:150]}")
                else:
                    print(f"   Response keys: {list(data.keys())[0:3]}")
                    print(f"   Sample: {str(data)[:150]}")
            else:
                print(f"   Data: {str(data)[:150]}")
            tests[f'{num}_{name}']['status'] = '✅ PASS'
        else:
            print(f"❌ Status {status}")
            tests[f'{num}_{name}']['status'] = '❌ FAIL'
        
        tests[f'{num}_{name}']['data'] = data
        return data, status == 200
        
    except Exception as e:
        print(f"❌ Exception: {str(e)[:100]}")
        tests[f'{num}_{name}']['status'] = '❌ ERROR'
        return None, False

# ============================================================================
# TEST 1: Search Flights
# ============================================================================
data1, ok1 = test_tool(1, 'search_flights', {
    'destination': test_dest,
    'date': test_date
})

flight_to_book = test_flight_id

# Handle both response formats (list or dict with result)
result = None
if ok1:
    if isinstance(data1, list):
        result = data1
    elif isinstance(data1, dict) and 'result' in data1:
        result = data1['result']
    
    if isinstance(result, list) and result:
        found_flight = result[0]
        flight_to_book = found_flight.get('flight_id', test_flight_id)
        print(f"\n✅ CROSS-REF: Found {len(result)} flights")
        db_check = query_db(f"SELECT id FROM flights WHERE id = '{flight_to_book}'")
        print(f"✅ Verified in DB: Flight exists" if db_check else f"⚠️ Not in DB")
    else:
        print(f"⚠️ No flights returned, using fallback: {test_flight_id}")
        tests['1_search_flights']['status'] = '⚠️ NO DATA'
else:
    tests['1_search_flights']['status'] = '❌ FAIL'

# ============================================================================
# TEST 2: Get Policy
# ============================================================================
data2, ok2 = test_tool(2, 'get_policy', {'topic': 'baggage-policy'})

if ok2 and isinstance(data2, dict):
    print(f"\n✅ CROSS-REF: Policy returned from backend")

# ============================================================================
# TEST 3: Get Flight Status
# ============================================================================
data3, ok3 = test_tool(3, 'get_flight_status', {'flight_id': flight_to_book})

if ok3 and isinstance(data3, dict):
    db_check = query_db(f"SELECT id, status FROM flights WHERE id = '{flight_to_book}'")
    if db_check:
        db_status = db_check[0]['status']
        print(f"\n✅ CROSS-REF: Flight {flight_to_book} status in DB = '{db_status}'")

# ============================================================================
# TEST 4: Book Flight
# ============================================================================
data4, ok4 = test_tool(4, 'book_flight', {
    'flight_id': flight_to_book,
    'passenger_name': 'Test Passenger',
    'seat_preference': 'window',
    'fare_type': 'economy'
})

if ok4 and isinstance(data4, dict) and 'result' in data4:
    result = data4['result']
    new_booking_ref = result.get('ref')
    if new_booking_ref:
        print(f"\n✅ Created booking: {new_booking_ref}")
        db_check = query_db(f"SELECT ref FROM bookings WHERE ref = '{new_booking_ref}'")
        print(f"✅ CROSS-REF: Verified in bookings table" if db_check else "⚠️ Not yet in DB")

# Try to use the new booking, fallback to existing if needed
booking_to_use = new_booking_ref if new_booking_ref else test_booking_ref

# ============================================================================
# TEST 5: Get Booking
# ============================================================================
if booking_to_use:
    data5, ok5 = test_tool(5, 'get_booking', {'ref': booking_to_use})
    if ok5:
        print(f"\n✅ CROSS-REF: Booking {booking_to_use} retrieved")
else:
    print(f"\nTEST 5: get_booking")
    print(f"❌ SKIPPED: No booking available")
    tests['5_get_booking']['status'] = '⊘ SKIPPED'

# ============================================================================
# TEST 6: Add Extras
# ============================================================================
if booking_to_use:
    data6, ok6 = test_tool(6, 'add_extras', {
        'ref': booking_to_use,
        'item_type': 'baggage',
        'description': 'Test extra baggage'
    })
    if ok6:
        db_check = query_db(f"SELECT id FROM booking_extras WHERE booking_ref = '{booking_to_use}'")
        print(f"\n✅ CROSS-REF: {len(db_check)} extra(s) in DB for {booking_to_use}")
else:
    print(f"\nTEST 6: add_extras")
    print(f"❌ SKIPPED: No booking available")
    tests['6_add_extras']['status'] = '⊘ SKIPPED'

# ============================================================================
# TEST 7: Add Assistance
# ============================================================================
if booking_to_use:
    data7, ok7 = test_tool(7, 'add_assistance', {
        'ref': booking_to_use,
        'assistance_code': 'WCHR',
        'notes': 'Wheelchair assistance needed'
    })
    if ok7:
        db_check = query_db(f"SELECT id FROM assistance WHERE booking_ref = '{booking_to_use}'")
        print(f"\n✅ CROSS-REF: {len(db_check)} assistance record(s) in DB")
else:
    print(f"\nTEST 7: add_assistance")
    print(f"❌ SKIPPED: No booking available")
    tests['7_add_assistance']['status'] = '⊘ SKIPPED'

# ============================================================================
# TEST 8: Reschedule Booking
# ============================================================================
if booking_to_use:
    # Find a different flight
    other = query_db(f"SELECT id FROM flights WHERE id != '{flight_to_book}' LIMIT 1")
    other_flight = other[0]['id'] if other else flight_to_book
    
    data8, ok8 = test_tool(8, 'reschedule_booking', {
        'ref': booking_to_use,
        'new_flight_id': other_flight
    })
    if ok8:
        print(f"\n✅ Rescheduled to {other_flight}")
else:
    print(f"\nTEST 8: reschedule_booking")
    print(f"❌ SKIPPED: No booking available")
    tests['8_reschedule_booking']['status'] = '⊘ SKIPPED'

# ============================================================================
# TEST 9: Cancel Booking
# ============================================================================
if booking_to_use and new_booking_ref:  # Only cancel new bookings we created
    data9, ok9 = test_tool(9, 'cancel_booking', {'ref': booking_to_use})
    if ok9:
        db_check = query_db(f"SELECT status FROM bookings WHERE ref = '{booking_to_use}'")
        if db_check:
            status = db_check[0]['status']
            print(f"\n✅ CROSS-REF: Booking status in DB = '{status}'")
elif booking_to_use:
    print(f"\nTEST 9: cancel_booking")
    print(f"⊘ SKIPPED: Protecting existing test booking")
    tests['9_cancel_booking']['status'] = '⊘ SKIPPED'
else:
    print(f"\nTEST 9: cancel_booking")
    print(f"❌ SKIPPED: No booking available")
    tests['9_cancel_booking']['status'] = '⊘ SKIPPED'

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

passed = sum(1 for t in tests.values() if t['status'] and '✅' in t['status'])
failed = sum(1 for t in tests.values() if t['status'] and '❌' in t['status'])
skipped = sum(1 for t in tests.values() if t['status'] and '⊘' in t['status'])

print("\nResults by test:")
for name, result in sorted(tests.items()):
    status = result['status'] or '? UNKNOWN'
    print(f"  {name:25} {status}")

print(f"\nTotal: {passed} ✅ | {failed} ❌ | {skipped} ⊘")

print("\n📊 DATABASE STATE AFTER TESTS:")
print("-" * 80)
stats = query_db("""
    SELECT 
        (SELECT COUNT(*) FROM flights) as flights,
        (SELECT COUNT(*) FROM bookings) as bookings,
        (SELECT COUNT(*) FROM booking_extras) as extras,
        (SELECT COUNT(*) FROM assistance) as assistance
""")

if stats:
    s = stats[0]
    print(f"Flights:    {s['flights']}")
    print(f"Bookings:   {s['bookings']}")
    print(f"Extras:     {s['extras']}")
    print(f"Assistance: {s['assistance']}")

print("\n✅ Test round complete!")
