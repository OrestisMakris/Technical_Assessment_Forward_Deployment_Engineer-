# 🎯 ElevenLabs Agent Configuration Guide

**Agent ID**: `agent_5401km1rxwwrfjtbw7ek6kp2yqrf`

## ⚠️ CRITICAL: Tool Configuration Issue

Your current webhook is receiving **only parameters** (`{'flight_id': ''}`) without a tool name. This means tools are **NOT configured** in ElevenLabs.

## ✅ How to Fix: Configure Tools in ElevenLabs Dashboard

1. **Go to**: https://elevenlabs.io/app/conversational-ai
2. **Select your agent**: `agent_5401km1rxwwrfjtbw7ek6kp2yqrf`
3. **Click**: "Settings" or "Tools" section
4. **Set Webhook URL**: 
   ```
   https://semiacidified-pansophically-charmain.ngrok-free.dev/webhook/elevenlabs
   ```

5. **Add Each Tool** (9 total) with these settings:

### Tool 1: `search_flights`
- **Name**: `search_flights`
- **Description**: Search for available flights by destination, date, and price
- **Server URL**: `https://semiacidified-pansophically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters** (JSON Schema):
  ```json
  {
    "type": "object",
    "properties": {
      "destination": {
        "type": "string",
        "description": "Destination city (e.g., Tokyo, Paris, New York)"
      },
      "departure_date": {
        "type": "string",
        "description": "Departure date YYYY-MM-DD"
      },
      "max_price": {
        "type": "number",
        "description": "Maximum price in GBP"
      }
    },
    "required": ["destination"]
  }
  ```

### Tool 2: `book_flight`
- **Name**: `book_flight`
- **Description**: Book a flight for a passenger
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "flight_id": {
        "type": "string",
        "description": "Flight ID (e.g., TM-FL-001)"
      },
      "passenger_name": {
        "type": "string",
        "description": "Full passenger name"
      },
      "seat_preference": {
        "type": "string",
        "enum": ["window", "aisle", "extra_legroom"],
        "description": "Seat preference"
      }
    },
    "required": ["flight_id", "passenger_name"]
  }
  ```

### Tool 3: `get_booking`
- **Name**: `get_booking`
- **Description**: View booking details by reference number
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "booking_ref": {
        "type": "string",
        "description": "Booking reference (e.g., TM-4821)"
      }
    },
    "required": ["booking_ref"]
  }
  ```

### Tool 4: `cancel_booking`
- **Name**: `cancel_booking`
- **Description**: Cancel an existing booking
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "booking_ref": {
        "type": "string",
        "description": "Booking reference to cancel"
      }
    },
    "required": ["booking_ref"]
  }
  ```

### Tool 5: `reschedule_booking`
- **Name**: `reschedule_booking`
- **Description**: Reschedule a booking to a different flight
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "booking_ref": {
        "type": "string",
        "description": "Current booking reference"
      },
      "new_flight_id": {
        "type": "string",
        "description": "New flight ID (e.g., TM-FL-002)"
      }
    },
    "required": ["booking_ref", "new_flight_id"]
  }
  ```

### Tool 6: `add_extras`
- **Name**: `add_extras`
- **Description**: Add extra services to a booking (luggage, lounge, etc.)
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "booking_ref": {
        "type": "string",
        "description": "Booking reference"
      },
      "extra_name": {
        "type": "string",
        "description": "Extra service name"
      },
      "quantity": {
        "type": "integer",
        "description": "Quantity"
      }
    },
    "required": ["booking_ref", "extra_name"]
  }
  ```

### Tool 7: `add_assistance`
- **Name**: `add_assistance`
- **Description**: Add special assistance (wheelchair, unaccompanied minor, etc.)
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "booking_ref": {
        "type": "string",
        "description": "Booking reference"
      },
      "type": {
        "type": "string",
        "description": "Assistance type"
      }
    },
    "required": ["booking_ref", "type"]
  }
  ```

### Tool 8: `get_flight_status`
- **Name**: `get_flight_status`
- **Description**: Check the status of a flight
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "flight_id": {
        "type": "string",
        "description": "Flight ID"
      }
    },
    "required": ["flight_id"]
  }
  ```

### Tool 9: `get_policy`
- **Name**: `get_policy`
- **Description**: Get airline policies (cancellation, baggage, etc.)
- **Server URL**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
- **Parameters**:
  ```json
  {
    "type": "object",
    "properties": {
      "topic": {
        "type": "string",
        "enum": ["cancellation", "baggage", "refund", "rebooking", "pet_policy"],
        "description": "Policy topic to retrieve"
      }
    },
    "required": ["topic"]
  }
  ```

## ✅ After Configuration

Once all 9 tools are added in ElevenLabs:

1. **Test the webhook** again (use "Test Tool" in ElevenLabs dashboard)
2. **Check the logs** - you should now see:
   ```
   ElevenLabs webhook received: {'tool_name': 'search_flights', 'parameters': {...}}
   ```
3. **The tool name should appear** in the logs (currently it's empty)

## 📝 Notes

- **Webhook URL** must include `/webhook/elevenlabs` endpoint
- Replace ngrok URL if tunnel restarts (URL changes every restart)
- The tool name in ElevenLabs **MUST MATCH** exactly:
  - `search_flights` (not `SearchFlights` or `search-flights`)
  - `book_flight` (not `BookFlight` or `book-flight`)
  - etc.

## 🔍 Debugging

If tools still don't work after configuration:

1. Check logs show the full payload with `tool_name`
2. Verify tool names **exactly match** the dispatch dictionary in [backend/routes/knowledge.py](backend/routes/knowledge.py)
3. Verify webhook URL is **exactly**: `https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs`
