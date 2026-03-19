"""
Test the actual loop's elevenlabs_client to see if it works now
"""

import asyncio
import logging
from refinement_loop.elevenlabs_client import run_conversation

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

async def main():
    print("\n" + "=" * 80)
    print("TESTING LOOP'S ELEVENLABS CLIENT")
    print("=" * 80 + "\n")
    
    # Simulate customer script (like the loop generates)
    customer_turns = [
        "Hello, I'd like to book a flight to Tokyo please.",
        "I'm flexible with dates.",
        "Can you book me on flight FL-201?",
        "Thanks a lot!",
    ]
    
    print(f"Customer script ({len(customer_turns)} turns):")
    for i, turn in enumerate(customer_turns, 1):
        print(f"  {i}. {turn}")
    
    print("\n" + "=" * 80)
    print("Running conversation...")
    print("=" * 80 + "\n")
    
    try:
        transcript = await run_conversation(customer_turns)
        
        print("\n" + "=" * 80)
        print("CONVERSATION RESULT")
        print("=" * 80)
        
        print(f"\nTotal turns captured: {len(transcript.turns)}")
        
        if transcript.turns:
            print("\nTranscript:")
            for i, turn in enumerate(transcript.turns, 1):
                role = "👥 CUSTOMER" if turn.role == "customer" else "🤖 AGENT"
                content = turn.content
                if len(content) > 80:
                    content = content[:80] + "..."
                print(f"  {i}. {role}")
                print(f"     {content}")
            
            # Check if conversation was successful
            agent_turns = sum(1 for t in transcript.turns if t.role == "agent")
            customer_turns_received = sum(1 for t in transcript.turns if t.role == "customer")
            
            print(f"\n✅ Success!")
            print(f"   Customer messages: {customer_turns_received}")
            print(f"   Agent responses: {agent_turns}")
        else:
            print("\n❌ No turns captured - conversation failed")
    
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
