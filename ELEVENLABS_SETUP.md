# 🛠️ ELEVENLABS AGENT SETUP GUIDE

## Step 1: Set the Webhook URL ✅

**Your ngrok URL:**
```
https://semiacidified-pansophically-charmain.ngrok-free.dev/webhook/elevenlabs
```

### Instructions:
1. Go to **ElevenLabs** → **Conversational AI** → Your Agent
2. Click **Tools** tab at the bottom
3. Find **"Server URL" or "Webhook"** field
4. **Paste your ngrok URL** (above)
5. **Save**

---

## Step 2: Add the 9 Tools

For **each tool below**:
1. Click **"+ Add tool"**
2. Choose **"Webhook"**
3. Set **Name** (exactly as shown)
4. Set **Method** to **POST**
5. Add the **parameters** (copy-paste)
6. **Save**

---

### Tool 1: search_flights
**Name:** `search_flights`  
**Method:** `POST`  
**Parameters:**
```json
{
  "destination": "City name e.g. Tokyo",
  "date": "YYYY-MM-DD format",
  "cheapest": "true to return only cheapest flight"
}
```

---

### Tool 2: book_flight
**Name:** `book_flight`  
**Method:** `POST`  
**Parameters:**
```json
{
  "flight_id": "Flight ID e.g. TM-FL-001",
  "passenger_name": "Full name of passenger",
  "seat_preference": "window, aisle, or extra_legroom (optional)"
}
```

---

### Tool 3: get_booking
**Name:** `get_booking`  
**Method:** `POST`  
**Parameters:**
```json
{
  "booking_ref": "Booking reference e.g. TM-4821"
}
```

---

### Tool 4: cancel_booking
**Name:** `cancel_booking`  
**Method:** `POST`  
**Parameters:**
```json
{
  "booking_ref": "Booking reference to cancel"
}
```

---

### Tool 5: reschedule_booking
**Name:** `reschedule_booking`  
**Method:** `POST`  
**Parameters:**
```json
{
  "booking_ref": "Existing booking reference",
  "new_flight_id": "New flight ID to reschedule to"
}
```

---

### Tool 6: add_extras
**Name:** `add_extras`  
**Method:** `POST`  
**Parameters:**
```json
{
  "booking_ref": "Booking reference",
  "item_type": "extra_bag, pram, sports_equipment, or oversized",
  "description": "Item description (optional)"
}
```

---

### Tool 7: add_assistance
**Name:** `add_assistance`  
**Method:** `POST`  
**Parameters:**
```json
{
  "booking_ref": "Booking reference",
  "assistance_code": "WCHR, WCHS, WCHC, BLND, DEAF, etc.",
  "notes": "Additional notes (optional)"
}
```

---

### Tool 8: get_flight_status
**Name:** `get_flight_status`  
**Method:** `POST`  
**Parameters:**
```json
{
  "flight_id": "Flight ID e.g. TM-FL-001"
}
```

---

### Tool 9: get_policy
**Name:** `get_policy`  
**Method:** `POST`  
**Parameters:**
```json
{
  "topic": "pet-policy, baggage-policy, checkin-policy, cancellation-policy, assistance-policy, etc."
}
```

---

## ✅ Checklist

- [ ] Webhook URL set to: `https://semiacidified-pansophically-charmain.ngrok-free.dev/webhook/elevenlabs`
- [ ] All 9 tools added with correct names
- [ ] All tools set to **POST** method
- [ ] Parameters match the examples above
- [ ] Agent saved

---

## 🧪 Test It

Once tools are configured:

1. **Open browser**: `http://localhost:8000`
2. **Click "START LOOP"**
3. Watch the observer UI show conversations
4. The agent will call your tools during conversations
5. Check ngrok terminal to see tool calls coming through

---

## 🐛 Troubleshooting

**Agent says "Tool failed":**
- Check ngrok is still running (`python start_ngrok.py`)
- Verify webhook URL is correct in ElevenLabs
- Tool name must match exactly (case-sensitive)

**Webhook returns error:**
- Check terminal 1 (uvicorn) for error logs
- Parameters might be wrong format
- Check API is responding: `curl http://localhost:8000/docs`

**Tool not found:**
- Make sure tool name matches exactly (example: `search_flights` not `SearchFlights`)

---

Ready? Update ElevenLabs and let's run the loop! 🚀
