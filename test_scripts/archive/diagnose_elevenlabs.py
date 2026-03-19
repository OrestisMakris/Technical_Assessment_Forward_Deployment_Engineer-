#!/usr/bin/env python
"""
Diagnostic tool for ElevenLabs agent troubleshooting.

This script tests:
1. Agent health check (is the agent responding?)
2. Prompt retrieval (is the prompt properly configured?)
3. Text-mode WebSocket connection
4. Single turn conversation
5. Multi-turn conversation

Run this FIRST to understand what's broken before running the full loop.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.getcwd())

from refinement_loop.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_AGENT_ID,
    ELEVENLABS_CONFIGURED,
)
from refinement_loop.elevenlabs_client import (
    check_agent_health,
    get_current_prompt,
    run_conversation,
)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("diagnose")


async def diagnose():
    """Run full diagnostics."""
    print("\n" + "=" * 80)
    print("🔍 ELEVENLABS AGENT DIAGNOSTICS")
    print("=" * 80)

    # Test 1: Configuration
    print("\n[TEST 1] Configuration Check")
    print("-" * 80)
    if not ELEVENLABS_CONFIGURED:
        print("❌ ELEVENLABS_API_KEY or ELEVENLABS_AGENT_ID not configured")
        print("   Set them in .env and retry")
        return
    else:
        print(f"✅ API Key configured: {ELEVENLABS_API_KEY[:20]}...")
        print(f"✅ Agent ID: {ELEVENLABS_AGENT_ID}")

    # Test 2: Agent Health
    print("\n[TEST 2] Agent Health Check")
    print("-" * 80)
    try:
        is_healthy = await check_agent_health()
        if is_healthy:
            print("✅ Agent is healthy and responding")
        else:
            print("❌ Agent is not responding properly")
            print("   Check the ElevenLabs dashboard to ensure the agent is deployed")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    # Test 3: Prompt Retrieval
    print("\n[TEST 3] Prompt Retrieval")
    print("-" * 80)
    try:
        prompt = await get_current_prompt()
        if prompt:
            prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
            print(f"✅ Current prompt retrieved ({len(prompt)} chars)")
            print(f"   Preview: {prompt_preview}")
        else:
            print("⚠️  Prompt is empty or not set")
    except Exception as e:
        print(f"❌ Failed to retrieve prompt: {e}")
        return

    # Test 4: Single-turn conversation
    print("\n[TEST 4] Single-turn Text-mode Conversation")
    print("-" * 80)
    try:
        customer_turns = ["Hello, I need to book a flight to Tokyo please."]
        print(f"Customer: {customer_turns[0]}")
        
        transcript = await run_conversation(customer_turns)
        
        print(f"\nTranscript captured: {len(transcript.turns)} turns")
        for turn in transcript.turns:
            role = "CUSTOMER" if turn.role == "customer" else "AGENT"
            text = turn.content if len(turn.content) < 100 else turn.content[:100] + "..."
            print(f"  {role}: {text}")
        
        if len(transcript.turns) >= 2:
            print("\n✅ Single-turn conversation successful")
        else:
            print("\n❌ Conversation failed - agent did not respond")
            print("   Possible causes:")
            print("   - WebSocket connection issues")
            print("   - Agent not processing text-mode input")
            print("   - Message format incorrect")
    except Exception as e:
        print(f"❌ Single-turn conversation failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Test 5: Multi-turn conversation
    print("\n[TEST 5] Multi-turn Conversation")
    print("-" * 80)
    try:
        customer_turns = [
            "Hi there! I want to book a flight to Paris.",
            "Next Friday works best for me.",
            "Economy class is fine. Can I have a window seat?",
            "Thanks, that sounds good. Can you book that for me?",
            "Great! Thanks so much.",
        ]
        
        print(f"Running {len(customer_turns)} turns...")
        transcript = await run_conversation(customer_turns)
        
        print(f"\n✅ Multi-turn conversation complete: {len(transcript.turns)} turns captured")
        print("\nFull transcript:")
        print("-" * 80)
        for turn in transcript.turns:
            role = "CUSTOMER" if turn.role == "customer" else "AGENT   "
            print(f"{role}: {turn.content}\n")
        
        if len(transcript.turns) >= len(customer_turns):
            print("✅ All customer turns were answered")
        else:
            print(f"⚠️  Only {len(transcript.turns)} / {len(customer_turns)} turns captured")
    except Exception as e:
        print(f"❌ Multi-turn conversation failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("🏁 Diagnostic complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(diagnose())
