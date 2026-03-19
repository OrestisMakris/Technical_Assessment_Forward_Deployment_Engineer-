"""
Configure ElevenLabs agent with all 9 flight booking tools via API.

This script uses the ElevenLabs Agents API to add tools to the agent.
See: https://elevenlabs.io/docs/conversational-ai/agents-api
"""

import json
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID")
API_KEY = os.getenv("ELEVENLABS_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://semiacidified-pansophistically-charmain.ngrok-free.dev/webhook/elevenlabs")

print(f"🚀 Configuring ElevenLabs Agent: {AGENT_ID}")
print(f"📍 Webhook URL: {WEBHOOK_URL}")
print(f"🔑 API Key: {API_KEY[:20]}...")

# ── Tool Definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "tool_name": "search_flights",
        "description": "Search for available flights based on criteria like destination, date, and seat class",
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destination city (e.g., 'Tokyo', 'Paris')"
                },
                "date": {
                    "type": "string",
                    "description": "Travel date in YYYY-MM-DD format"
                },
                "seat_class": {
                    "type": "string",
                    "description": "Seat class: 'economy', 'business', or 'first'"
                }
            },
            "required": ["destination"]
        }
    },
    {
        "tool_name": "book_flight",
        "description": "Book a flight for a customer",
        "parameters": {
            "type": "object",
            "properties": {
                "flight_id": {
                    "type": "string",
                    "description": "ID of the flight to book"
                },
                "passenger_name": {
                    "type": "string",
                    "description": "Name of the passenger"
                },
                "email": {
                    "type": "string",
                    "description": "Passenger email address"
                },
                "seat_class": {
                    "type": "string",
                    "description": "Seat class: 'economy', 'business', or 'first'"
                }
            },
            "required": ["flight_id", "passenger_name", "email"]
        }
    },
    {
        "tool_name": "get_booking",
        "description": "Retrieve booking details by booking reference",
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Booking reference number"
                }
            },
            "required": ["ref"]
        }
    },
    {
        "tool_name": "cancel_booking",
        "description": "Cancel an existing booking",
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Booking reference number"
                }
            },
            "required": ["ref"]
        }
    },
    {
        "tool_name": "reschedule_booking",
        "description": "Reschedule a booking to a different flight",
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Booking reference number"
                },
                "new_flight_id": {
                    "type": "string",
                    "description": "ID of the new flight"
                }
            },
            "required": ["ref", "new_flight_id"]
        }
    },
    {
        "tool_name": "add_extras",
        "description": "Add extras (baggage, meals) to a booking",
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Booking reference number"
                },
                "extra_type": {
                    "type": "string",
                    "description": "Type of extra: 'baggage', 'meal', 'seat_selection'"
                },
                "quantity": {
                    "type": "integer",
                    "description": "Quantity of the extra"
                }
            },
            "required": ["ref", "extra_type"]
        }
    },
    {
        "tool_name": "add_assistance",
        "description": "Add special assistance request to a booking",
        "parameters": {
            "type": "object",
            "properties": {
                "ref": {
                    "type": "string",
                    "description": "Booking reference number"
                },
                "assistance_type": {
                    "type": "string",
                    "description": "Type of assistance needed (e.g., 'wheelchair', 'unaccompanied_minor', 'pet_transport')"
                }
            },
            "required": ["ref", "assistance_type"]
        }
    },
    {
        "tool_name": "get_flight_status",
        "description": "Get the current status of a flight",
        "parameters": {
            "type": "object",
            "properties": {
                "flight_id": {
                    "type": "string",
                    "description": "ID of the flight"
                }
            },
            "required": ["flight_id"]
        }
    },
    {
        "tool_name": "get_policy",
        "description": "Get airline policies",
        "parameters": {
            "type": "object",
            "properties": {
                "policy_type": {
                    "type": "string",
                    "description": "Type of policy: 'baggage', 'pet', 'cancellation', 'checkin', 'assistance'"
                }
            },
            "required": ["policy_type"]
        }
    },
]


def add_tools_to_agent():
    """Add all 9 tools to the ElevenLabs agent."""
    
    client = httpx.Client(
        headers={"xi-api-key": API_KEY},
        timeout=30
    )
    
    # First get the agent to see current tools
    print("\n" + "="*80)
    print("📋 CHECKING CURRENT AGENT CONFIGURATION")
    print("="*80)
    
    resp = client.get(f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}")
    if resp.status_code != 200:
        print(f"❌ Failed to fetch agent: {resp.status_code}")
        print(resp.text)
        return False
    
    agent = resp.json()
    print(f"✅ Agent: {agent.get('name')}")
    print(f"   Current tools: {len(agent.get('tools', []))}")
    for tool in agent.get('tools', []):
        print(f"     - {tool.get('tool_name')}")
    
    # Now add/update tools
    print("\n" + "="*80)
    print("🔧 CONFIGURING TOOLS")
    print("="*80)
    
    for tool in TOOLS:
        # Create tool definition with webhook
        tool_payload = {
            "tool_name": tool["tool_name"],
            "description": tool["description"],
            "parameters": tool["parameters"],
            "webhook": {
                "url": WEBHOOK_URL,
                "method": "POST"
            }
        }
        
        print(f"\n📌 Adding tool: {tool['tool_name']}")
        
        # Try to update or create
        # ElevenLabs API: POST /v1/convai/agents/{AGENT_ID}/tools
        resp = client.post(
            f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}/tools",
            json=tool_payload
        )
        
        if resp.status_code in [200, 201]:
            print(f"   ✅ {tool['tool_name']} configured")
        else:
            print(f"   ⚠️  Status {resp.status_code}: {resp.text[:200]}")
            # Try alternative endpoint
            # Some versions use PUT instead of POST
            resp = client.put(
                f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}/tools/{tool['tool_name']}",
                json=tool_payload
            )
            if resp.status_code in [200, 201]:
                print(f"   ✅ {tool['tool_name']} configured (via PUT)")
            else:
                print(f"   ❌ Failed: {resp.status_code}")
    
    # Verify the tools were added
    print("\n" + "="*80)
    print("✅ VERIFICATION")
    print("="*80)
    
    resp = client.get(f"https://api.elevenlabs.io/v1/convai/agents/{AGENT_ID}")
    if resp.status_code == 200:
        agent = resp.json()
        tools = agent.get('tools', [])
        print(f"✅ Agent now has {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.get('tool_name')}")
        
        if len(tools) >= 9:
            print(f"\n🎉 SUCCESS: All {len(tools)} tools are configured!")
            return True
        else:
            print(f"\n⚠️  Only {len(tools)}/9 tools configured. Check API response above.")
            return False
    else:
        print(f"❌ Failed to verify: {resp.status_code}")
        return False


if __name__ == "__main__":
    if not AGENT_ID or not API_KEY:
        print("❌ Missing ELEVENLABS_AGENT_ID or ELEVENLABS_API_KEY in .env")
        exit(1)
    
    success = add_tools_to_agent()
    
    if success:
        print("\n" + "="*80)
        print("🚀 NEXT STEPS:")
        print("="*80)
        print("""
1. Restart the loop with: python run_and_monitor_loop.py
2. The agent should now respond to tool calls
3. Monitor webhook logs to see tool invocations
        """)
    else:
        print("\n" + "="*80)
        print("❌ TROUBLESHOOTING:")
        print("="*80)
        print("""
1. Check if ElevenLabs API is accessible
2. Verify ELEVENLABS_API_KEY is correct
3. Check if ngrok tunnel is still active
4. Try configuring tools manually in ElevenLabs UI

Manual steps:
1. Go to ElevenLabs dashboard
2. Select your agent
3. Add tools section and paste tool configurations
4. Use the webhook URL: """ + WEBHOOK_URL)
