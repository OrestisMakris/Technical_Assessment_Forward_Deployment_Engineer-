"""
Update ElevenLabs agent system prompt to include tool information.

The agent needs to know about available tools via its system prompt.
We'll fetch the current prompt and add tool descriptions.
"""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs")

TOOL_INSTRUCTIONS = """
## Available Tools

You have access to the following tools via API calls. Use them to help customers with flight bookings:

### Flight Search & Status
- **search_flights(destination, date?, seat_class?)**: Search for available flights. Returns list of flights with pricing.
- **get_flight_status(flight_id)**: Get current status of a flight (on-time, delayed, cancelled).

### Booking Management
- **book_flight(flight_id, passenger_name, email, seat_class?)**: Book a flight for a customer. Returns booking reference.
- **get_booking(ref)**: Retrieve details of an existing booking by reference number.
- **cancel_booking(ref)**: Cancel a booking. Returns refund information.
- **reschedule_booking(ref, new_flight_id)**: Change a booking to a different flight.

### Add-ons & Services
- **add_extras(ref, extra_type, quantity?)**: Add baggage, meals, or seat selection to a booking.
- **add_assistance(ref, assistance_type)**: Add special assistance (wheelchair, unaccompanied_minor, pet_transport).

### Policies
- **get_policy(policy_type)**: Get airline policy information. Types: baggage, pet, cancellation, checkin, assistance.

## Tool Usage Guidelines

1. **Always search first**: When a customer wants to book, search for flights matching their criteria before showing options.
2. **Confirm before booking**: Show flight details and ask for confirmation before making a booking.
3. **Use proper values**: 
   - Date format: YYYY-MM-DD
   - Seat classes: economy, business, first
   - Extra types: baggage, meal, seat_selection
4. **Handle errors gracefully**: If a tool call fails, explain to the customer what went wrong.
5. **Provide booking reference**: Always give the customer their booking reference (ref) after successful booking.

## Conversation Style

- Be friendly and professional
- Break down flight options clearly (airline, time, price, duration)
- Confirm details before taking action
- Provide booking reference clearly
- Answer policy questions accurately
"""

def update_system_prompt():
    """Update the agent's system prompt to include tool information."""
    
    print(f"🚀 Updating ElevenLabs Agent system prompt: {AGENT_ID}")
    
    client = httpx.Client(
        headers={"xi-api-key": API_KEY},
        timeout=30
    )
    
    # Get current agent
    print("\n📖 Fetching current agent configuration...")
    resp = client.get(f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}")
    
    if resp.status_code != 200:
        print(f"❌ Failed to fetch agent: {resp.status_code}")
        print(resp.text)
        return False
    
    agent = resp.json()
    current_prompt = agent.get('system_prompt', '')
    print(f"✅ Current prompt length: {len(current_prompt)} chars")
    
    # Combine prompts
    new_prompt = current_prompt + "\n\n" + TOOL_INSTRUCTIONS if current_prompt else TOOL_INSTRUCTIONS
    
    print(f"\n📝 New prompt length: {len(new_prompt)} chars")
    
    # Update agent
    # Note: The agent update endpoint varies by ElevenLabs version
    # Try PATCH first, then PUT
    
    payload = {
        "system_prompt": new_prompt
    }
    
    print(f"\n🔄 Attempting to update agent system prompt...")
    
    # Try PATCH
    resp = client.patch(
        f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}",
        json=payload
    )
    
    if resp.status_code == 404:
        print(f"   PATCH endpoint not found, trying PUT...")
        resp = client.put(
            f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}",
            json=payload
        )
    
    if resp.status_code in [200, 201]:
        print(f"✅ Successfully updated system prompt!")
        print(f"\n📋 Updated prompt includes:")
        print(f"   - Search flights tool")
        print(f"   - Flight status checking")
        print(f"   - Book, cancel, reschedule bookings")
        print(f"   - Add extras and assistance")
        print(f"   - Policy queries")
        return True
    else:
        print(f"❌ Failed to update: {resp.status_code}")
        print(f"   Response: {resp.text[:300]}")
        return False

def print_manual_instructions():
    """Print manual UI instructions if API fails."""
    
    print("\n" + "=" * 80)
    print("📘 MANUAL CONFIGURATION INSTRUCTIONS")
    print("=" * 80)
    print("""
Since tools cannot be configured via API, you must add them manually:

OPTION 1: Configure tools in ElevenLabs UI
-------------------------------------------
1. Go to: https://elevenlabs.io/app/conversational-ai
2. Select agent: "Airline Assistant Agent"
3. Click "Tools" or "Add Tool"
4. Create each tool with these webhooks:
   - Tool Name: search_flights
   - Webhook: """ + WEBHOOK_URL + """
   - Parameters: { "destination": "string", "date": "string", "seat_class": "string" }
   
   (Repeat for all 9 tools - see below)

OPTION 2: Update system prompt to guide agent
----------------------------------------------
The agent needs to know WHICH tools are available.
Add this to the system prompt:

[PASTE THE TOOL INSTRUCTIONS ABOVE]

OPTION 3: Use agents-api (if available)
----------------------------------------
If you have access to agents-api, use:
curl -X POST https://api.elevenlabs.io/v1/agents/{AGENT_ID}/tools \\
  -H "xi-api-key: YOUR_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{...tool_definition...}'

ALL 9 TOOLS:
------------
1. search_flights
2. book_flight
3. get_booking
4. cancel_booking
5. reschedule_booking
6. add_extras
7. add_assistance
8. get_flight_status
9. get_policy

Webhook for all: """ + WEBHOOK_URL)

if __name__ == "__main__":
    if not AGENT_ID or not API_KEY:
        print("❌ Missing env variables")
        exit(1)
    
    # Try to update via API
    success = update_system_prompt()
    
    if not success:
        print_manual_instructions()
    else:
        print("\n" + "=" * 80)
        print("✅ SYSTEM PROMPT UPDATED")
        print("=" * 80)
        print("""
The agent now has instructions about available tools.

NEXT: You can now either:
A) Restart the loop to test if the agent knows to use tools
B) Configure tools in ElevenLabs UI for explicit tool support

Try restarting the loop with:
  python run_and_monitor_loop.py
""")
