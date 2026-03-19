#!/usr/bin/env python3
"""
QUICK TEST — Simplest possible test of the loop with backend server.

This script:
1. Starts the FastAPI backend server (required for webhook tools)
2. Checks ElevenLabs credentials
3. Runs ONE customer scenario
4. Shows the full conversation
5. Evaluates the conversation
6. Shows if it passed

Takes about 2-3 minutes.

Run: python test_quick.py
"""

import asyncio
import logging
import sys
import subprocess
import time
from pathlib import Path

# Simple logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)

from refinement_loop.config import ELEVENLABS_AGENT_ID, ELEVENLABS_API_KEY, GOOGLE_API_KEY
from refinement_loop.scenarios import SCENARIOS
from refinement_loop.simulator import generate_customer_script, simulate
from refinement_loop.evaluator import evaluate_all
from refinement_loop.loop import RefinementLoop


def start_backend():
    """Start the FastAPI backend server in a subprocess."""
    logger.info("Starting FastAPI backend server on http://localhost:8000...")
    try:
        # Start uvicorn server
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Give the server time to start
        time.sleep(3)
        
        # Check if server is running
        try:
            import httpx
            response = httpx.get("http://localhost:8000/docs", timeout=2)
            if response.status_code == 200:
                logger.info("✅ Backend server is running")
                return proc
        except:
            pass
        
        logger.warning("⚠️ Backend server may not have started properly, but continuing anyway...")
        return proc
    except Exception as e:
        logger.warning(f"⚠️ Failed to start backend server: {e}")
        logger.warning("   The test will continue but webhook tools may not work")
        return None


async def main():
    backend_proc = None
    try:
        # Start backend server
        logger.info("\n0️⃣  Starting backend server...")
        backend_proc = start_backend()
        
        logger.info("\n" + "=" * 80)
        logger.info("QUICK TEST - Single Scenario")
        logger.info("=" * 80)
        
        # Check credentials
        logger.info("\n1️⃣  Checking credentials...")
        if not ELEVENLABS_API_KEY:
            logger.error("❌ ELEVENLABS_API_KEY not set")
            logger.error("   Set it: export ELEVENLABS_API_KEY=<key>")
            return False
        if not ELEVENLABS_AGENT_ID:
            logger.error("❌ ELEVENLABS_AGENT_ID not set")
            logger.error("   Set it: export ELEVENLABS_AGENT_ID=<id>")
            return False
        if not GOOGLE_API_KEY:
            logger.error("❌ GOOGLE_API_KEY not set")
            logger.error("   Set it: export GOOGLE_API_KEY=<key>")
            return False
        logger.info("✓ Credentials are set")
        
        # Load system prompt
        logger.info("\n2️⃣  Loading system prompt...")
        system_prompt = RefinementLoop._load_prompt()
        logger.info(f"✓ Loaded prompt ({len(system_prompt)} chars)")
        
        # Pick first scenario
        scenario = SCENARIOS[0]
        logger.info(f"\n3️⃣  Testing scenario: {scenario.id.replace('_', ' ').upper()}")
        logger.info(f"   Goal: {scenario.customer_goal}")
        
        # Generate customer script
        logger.info("\n4️⃣  Generating customer script (using Gemini)...")
        try:
            customer_utterances = generate_customer_script(scenario)
            logger.info(f"✓ Generated {len(customer_utterances)} utterances")
            for i, u in enumerate(customer_utterances, 1):
                logger.info(f"   {i}. {u[:70]}")
        except Exception as e:
            logger.error(f"❌ Failed to generate script: {e}")
            return False
        
        # Run conversation
        logger.info("\n5️⃣  Running conversation with ElevenLabs agent...")
        logger.info("   (This will take 1-2 minutes)")
        try:
            transcript = await simulate(scenario, system_prompt)
            logger.info(f"✓ Conversation complete: {len(transcript.turns)} turns")
            
            if not transcript.turns:
                logger.error("❌ Conversation produced 0 turns!")
                logger.error("   Check your ElevenLabs agent configuration")
                return False
            
            logger.info("\n   Conversation transcript:")
            for i, turn in enumerate(transcript.turns, 1):
                role = "CUSTOMER" if turn.role == "customer" else "AGENT"
                content = turn.content[:80] + ("..." if len(turn.content) > 80 else "")
                logger.info(f"   [{role}]: {content}")
        
        except Exception as e:
            logger.error(f"❌ Conversation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Evaluate
        logger.info("\n6️⃣  Evaluating conversation...")
        try:
            evaluations = evaluate_all([transcript], iteration=1)
            
            for eval_result in evaluations:
                logger.info(f"✓ Evaluation complete")
                logger.info(f"   Overall score: {eval_result.overall_score:.1f}/10")
                logger.info(f"   Passed: {'YES' if eval_result.passed else 'NO'}")
                logger.info(f"   Root cause: {eval_result.root_cause.value}")
                logger.info(f"\n   Scores per criterion:")
                for score in eval_result.scores:
                    status = "OK" if score.score >= 8.0 else "FAIL"
                    logger.info(f"     [{status}] {score.name:20} {score.score:>5.1f}  {score.rationale}")
        
        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        logger.info("\n" + "=" * 80)
        logger.info("OK: QUICK TEST PASSED")
        logger.info("=" * 80)
        logger.info("\nThe loop infrastructure is working correctly!")
        logger.info("\nNext step: Run the full loop")
        logger.info("  python start_loop.py")
        
        return True
    
    finally:
        # Clean up backend process if started
        if backend_proc:
            try:
                logger.info("\nShutting down backend server...")
                backend_proc.terminate()
                backend_proc.wait(timeout=5)
            except:
                backend_proc.kill()



if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
