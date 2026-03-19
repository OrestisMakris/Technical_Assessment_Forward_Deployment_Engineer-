#!/usr/bin/env python
"""
🧪 COMPREHENSIVE TEST CASES FOR ALL 9 ELEVENLABS TOOLS

Based on actual database data. Use these exact parameters in the ElevenLabs test tool.
"""

# ============================================================================
# TOOL 1: search_flights
# ============================================================================
TOOL_1_search_flights = {
    "name": "search_flights",
    "description": "Search available flights by destination, date, or price",
    "test_cases": [
        {
            "name": "Search Paris economy flights",
            "params": {
                "destination": "Paris",
                "seat_class": "economy",
                "origin": "London"
            },
            "expected": "List of economy flights to Paris from London"
        },
        {
            "name": "Search cheapest Tokyo flight",
            "params": {
                "destination": "Tokyo",
                "cheapest": True
            },
            "expected": "Single cheapest flight to Tokyo (should be ~£595)"
        },
        {
            "name": "Search specific date",
            "params": {
                "destination": "Paris",
                "date": "2026-03-19"
            },
            "expected": "Flights to Paris on 2026-03-19"
        },
        {
            "name": "Search business class",
            "params": {
                "destination": "Tokyo",
                "seat_class": "business"
            },
            "expected": "Business class flights to Tokyo"
        }
    ]
}

# ============================================================================
# TOOL 2: book_flight
# ============================================================================
TOOL_2_book_flight = {
    "name": "book_flight",
    "description": "Book a flight for a passenger",
    "test_cases": [
        {
            "name": "Book economy flight with window seat",
            "params": {
                "flight_id": "TM-FL-010",
                "passenger_name": "Alice Johnson",
                "seat_preference": "window"
            },
            "expected": "Returns new booking reference (e.g., TM-XXXX)"
        },
        {
            "name": "Book aisle seat",
            "params": {
                "flight_id": "TM-FL-002",
                "passenger_name": "Bob Williams",
                "seat_preference": "aisle"
            },
            "expected": "New booking with aisle seat assigned"
        }
    ]
}

# ============================================================================
# TOOL 3: get_booking
# ============================================================================
TOOL_3_get_booking = {
    "name": "get_booking",
    "description": "View booking details by reference number",
    "test_cases": [
        {
            "name": "Check existing booking TM-4821",
            "params": {
                "ref": "TM-4821"
            },
            "expected": "Full booking details: flight, passenger name, seat, price"
        },
        {
            "name": "Check booking TM-3301",
            "params": {
                "ref": "TM-3301"
            },
            "expected": "Booking information for TM-3301"
        }
    ]
}

# ============================================================================
# TOOL 4: get_flight_status
# ============================================================================
TOOL_4_get_flight_status = {
    "name": "get_flight_status",
    "description": "Check the status and gate information of a flight",
    "test_cases": [
        {
            "name": "Check Tokyo flight status",
            "params": {
                "flight_id": "TM-FL-001"
            },
            "expected": "Status (on_time), gate assignment if within 24h, passenger count"
        },
        {
            "name": "Check Paris flight",
            "params": {
                "flight_id": "TM-FL-010"
            },
            "expected": "Flight status and occupancy info"
        }
    ]
}

# ============================================================================
# TOOL 5: cancel_booking
# ============================================================================
TOOL_5_cancel_booking = {
    "name": "cancel_booking",
    "description": "Cancel an existing booking",
    "test_cases": [
        {
            "name": "Cancel booking TM-6610",
            "params": {
                "ref": "TM-6610"
            },
            "expected": "Booking cancelled, refund processed"
        }
    ]
}

# ============================================================================
# TOOL 6: reschedule_booking
# ============================================================================
TOOL_6_reschedule_booking = {
    "name": "reschedule_booking",
    "description": "Reschedule a booking to a different flight",
    "test_cases": [
        {
            "name": "Reschedule to different Paris flight",
            "params": {
                "ref": "TM-3301",
                "new_flight_id": "TM-FL-012"
            },
            "expected": "Booking rescheduled to TM-FL-012"
        },
        {
            "name": "Reschedule to different date",
            "params": {
                "ref": "TM-4821",
                "new_flight_id": "TM-FL-011"
            },
            "expected": "Booking updated with new flight"
        }
    ]
}

# ============================================================================
# TOOL 7: add_extras
# ============================================================================
TOOL_7_add_extras = {
    "name": "add_extras",
    "description": "Add extras like baggage or seat upgrades to a booking",
    "test_cases": [
        {
            "name": "Add checked baggage",
            "params": {
                "ref": "TM-4821",
                "item_type": "extra_bag",
                "description": "Additional checked baggage (23kg)"
            },
            "expected": "Extra baggage added to booking, fee applied"
        },
        {
            "name": "Add seat upgrade",
            "params": {
                "ref": "TM-3301",
                "item_type": "seat_upgrade",
                "description": "Upgrade to extra legroom seat"
            },
            "expected": "Seat upgrade applied to booking"
        }
    ]
}

# ============================================================================
# TOOL 8: add_assistance
# ============================================================================
TOOL_8_add_assistance = {
    "name": "add_assistance",
    "description": "Add special assistance to a booking (wheelchair, hearing aid, etc.)",
    "test_cases": [
        {
            "name": "Request wheelchair assistance",
            "params": {
                "ref": "TM-4821",
                "assistance_code": "WCHR",
                "notes": "Wheelchair needed at airport and on aircraft"
            },
            "expected": "Wheelchair assistance confirmed"
        },
        {
            "name": "Request unaccompanied minor support",
            "params": {
                "ref": "TM-6610",
                "assistance_code": "UMNR",
                "notes": "13-year-old traveling alone"
            },
            "expected": "Minor support assistance recorded"
        }
    ]
}

# ============================================================================
# TOOL 9: get_policy
# ============================================================================
TOOL_9_get_policy = {
    "name": "get_policy",
    "description": "Look up airline policies on baggage, cancellation, pets, etc.",
    "test_cases": [
        {
            "name": "Check baggage policy",
            "params": {
                "topic": "baggage_policy"
            },
            "expected": "Baggage allowances by fare type"
        },
        {
            "name": "Check cancellation policy",
            "params": {
                "topic": "cancellation_refund_policy"
            },
            "expected": "Refund terms and cancellation deadlines"
        },
        {
            "name": "Check pet policy",
            "params": {
                "topic": "pet_policy"
            },
            "expected": "Rules for traveling with animals"
        },
        {
            "name": "Check special assistance",
            "params": {
                "topic": "special_assistance"
            },
            "expected": "Available assistance codes and services"
        },
        {
            "name": "Check seat policy",
            "params": {
                "topic": "seat_policy"
            },
            "expected": "Seat selection rules and extra legroom options"
        }
    ]
}

# ============================================================================
# SUMMARY TABLE
# ============================================================================

if __name__ == "__main__":
    tools = [TOOL_1_search_flights, TOOL_2_book_flight, TOOL_3_get_booking, 
             TOOL_4_get_flight_status, TOOL_5_cancel_booking, TOOL_6_reschedule_booking,
             TOOL_7_add_extras, TOOL_8_add_assistance, TOOL_9_get_policy]
    
    print("\n" + "=" * 100)
    print("🧪 ELEVENLABS WEBHOOK TEST CASES - COMPLETE REFERENCE")
    print("=" * 100)
    
    for i, tool in enumerate(tools, 1):
        print(f"\n{i}. {tool['name'].upper()}")
        print(f"   {tool['description']}")
        print(f"   Test cases: {len(tool['test_cases'])}")
        for j, tc in enumerate(tool['test_cases'], 1):
            params_str = ", ".join([f"{k}={repr(v)}" for k, v in tc['params'].items()])
            print(f"     {j}. {tc['name']}")
            print(f"        → {params_str}")
    
    print("\n" + "=" * 100)
    print("✅ Use these test cases in ElevenLabs agent Test Tool")
    print("=" * 100)
