"""
Test using the exact same ElevenLabs client code as the loop uses.
"""

import asyncio
import sys
from refinement_loop.elevenlabs_client import run_conversation

async def main():
    print("=" * 80)
    print("🔍 TESTING ACTUAL CONVERSATION WITH ELEVENLABS CLIENT")
    print("=" * 80)
    
    # Simple customer turns similar to what simulator generates
    customer_turns = [
        "Hi, I'd like to book a flight to Tokyo please.",
        "Sure, I'm flexible with dates.",
        "That works! Please book me on FL-201.",
        "Thanks! Have a great day!",
    ]
    
    print(f"\nCustomer turns: {len(customer_turns)}")
    for i, turn in enumerate(customer_turns, 1):
        print(f"  {i}. {turn}")
    
    print("\n" + "=" * 80)
    print("Starting conversation...")
    print("=" * 80 + "\n")
    
    try:
        transcript = await run_conversation(customer_turns)
        
        print("\n" + "=" * 80)
        print("CONVERSATION COMPLETE")
        print("=" * 80)
        print(f"\nTranscript turns: {len(transcript.turns)}")
        
        for i, turn in enumerate(transcript.turns, 1):
            role_icon = "👥" if turn.role == "customer" else "🤖"
            print(f"\n{i}. {role_icon} {turn.role.upper()}")
            print(f"   {turn.content[:100]}{'...' if len(turn.content) > 100 else ''}")
        
        if transcript.turns:
            print(f"\n✅ Conversation retrieved {len(transcript.turns)} turns")
        else:
            print(f"\n❌ No turns captured - agent did not respond")
    
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
