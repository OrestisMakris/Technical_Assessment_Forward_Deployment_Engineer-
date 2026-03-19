#!/usr/bin/env python
"""
Quick test of the refinement loop with one scenario.

Run this after fixing any issues to verify the system is working.
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.append(os.getcwd())

from refinement_loop.loop import RefinementLoop


async def test_one_scenario():
    """Test with just the first scenario to save time."""
    print("\n" + "=" * 80)
    print("🚀 REFINEMENT LOOP - SINGLE SCENARIO TEST")
    print("=" * 80)
    print("\nTesting with scenario: 'book_next_available'")
    print("(This is a quick smoke test - full loop takes longer)")
    
    # Run with just one scenario
    loop = RefinementLoop(scenario_ids=["book_next_available"])
    summary = await loop.run()
    
    print("\n" + "=" * 80)
    print("📊 TEST COMPLETE")
    print("=" * 80)
    print(f"\nReason: {summary.terminated_reason}")
    print(f"Iterations: {len(summary.iterations)}")
    
    if summary.iterations:
        last_iter = summary.iterations[-1]
        print(f"\nLast iteration scores:")
        for eval_result in last_iter.evaluations[:3]:  # Show first 3
            scores = {s.name: s.score for s in eval_result.scores}
            avg = sum(scores.values()) / len(scores)
            print(f"  Scenario: {eval_result.scenario_id}")
            print(f"    Average: {avg:.1f}/10")
            print(f"    Status: {'✅ PASSED' if eval_result.passed else '❌ FAILED'}")
    
    return summary.terminated_reason == "passed"


async def test_full_loop():
    """Run the full 10-scenario loop."""
    print("\n" + "=" * 80)
    print("🚀 REFINEMENT LOOP - FULL RUN (10 SCENARIOS)")
    print("=" * 80)
    print("\nWARNING: This will take several minutes!")
    print("(Recommended: run test_one_scenario() first)\n")
    
    response = input("Continue? (y/N): ").strip().lower()
    if response != "y":
        print("Cancelled.")
        return False
    
    # Run with all scenarios
    loop = RefinementLoop()
    summary = await loop.run()
    
    print("\n" + "=" * 80)
    print("✅ FULL LOOP COMPLETE")
    print("=" * 80)
    print(f"\nTerminated: {summary.terminated_reason}")
    print(f"Total iterations: {len(summary.iterations)}")
    
    all_passed = all(
        e.passed 
        for iter_result in summary.iterations 
        for e in iter_result.evaluations
    )
    print(f"Overall status: {'🎉 ALL PASSED' if all_passed else '⚠️  SOME FAILED'}")
    
    if summary.iterations:
        print(f"\nLog file: {Path('logs').absolute()}")
    
    return all_passed


if __name__ == "__main__":
    print("\n1️⃣  QUICK TEST (1 scenario, ~2 min)")
    print("2️⃣  FULL TEST (10 scenarios, ~15+ min)")
    choice = input("\nChoose test: ").strip()
    
    try:
        if choice == "1":
            result = asyncio.run(test_one_scenario())
        elif choice == "2":
            result = asyncio.run(test_full_loop())
        else:
            print("Invalid choice")
            sys.exit(1)
        
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\nAborted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
