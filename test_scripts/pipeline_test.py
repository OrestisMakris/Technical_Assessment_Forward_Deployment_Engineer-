#!/usr/bin/env python
"""
Complete pipeline test: sent → received → evaluated

Shows:
1. Messages sent to ElevenLabs
2. Messages received from ElevenLabs  
3. Transcript assembled locally
4. Gemini evaluator assessment
"""
import asyncio
import json
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.append(os.getcwd())

from refinement_loop.elevenlabs_client import run_conversation
from refinement_loop.evaluator import evaluate
from refinement_loop.scenarios import SCENARIOS

async def main():
    # Get first scenario
    scenario = SCENARIOS[0]  # "book_next_available"
    
    print("=" * 80)
    print("FULL PIPELINE TEST")
    print("=" * 80)
    print(f"\nScenario: {scenario.name}")
    print(f"Goal: {scenario.customer_goal}")
    
    # Pre-generated customer utterances (like simulator does)
    customer_turns = [
        "Hi, I'd like to book a flight to Tokyo for next week.",
        "Economy class is fine for me.",
        "Great, can you go ahead and book that flight?",
    ]
    
    print(f"\n--- STEP 1: MESSAGES TO SEND ---")
    for i, turn in enumerate(customer_turns, 1):
        print(f"{i}. CUSTOMER: {turn}")
    
    # Run conversation
    print(f"\n--- STEP 2: RUNNING CONVERSATION ---")
    transcript = await run_conversation(customer_turns)
    transcript.scenario_id = scenario.id  # Set scenario_id for evaluation
    
    # Show transcript
    print(f"\n--- STEP 3: TRANSCRIPT RECEIVED ---")
    print(f"Total turns captured: {len(transcript.turns)}")
    for i, turn in enumerate(transcript.turns, 1):
        role = "CUSTOMER" if turn.role == "customer" else "AGENT   "
        print(f"\n{i}. {role}:")
        print(f"   {turn.content if len(turn.content) < 100 else turn.content[:100] + '...'}")
        print(f"   (length: {len(turn.content)} chars)")
    
    # Evaluate
    print(f"\n--- STEP 4: GEMINI EVALUATION ---")
    try:
        eval_result = evaluate(transcript, iteration=1)
        
        print(f"\nScenario: {eval_result.scenario_id}")
        print(f"Overall Score: {eval_result.overall_score:.1f}/10")
        print(f"Passed: {eval_result.passed}")
        print(f"Root Cause: {eval_result.root_cause.value}")
        
        print(f"\nCriteria Scores:")
        for score in eval_result.scores:
            print(f"  {score.name}: {score.score}/10")
            if score.failure_quote:
                print(f"    Failure: {score.failure_quote}")
            print(f"    Rationale: {score.rationale}")
        
        print(f"\nRoot Cause Explanation:")
        print(f"  {eval_result.root_cause_explanation}")
        
        if eval_result.faulty_file:
            print(f"\nFaulty File: {eval_result.faulty_file}")
            print(f"Faulty Behavior: {eval_result.faulty_behaviour}")
    
    except Exception as e:
        print(f"\nEvaluation ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

asyncio.run(main())
