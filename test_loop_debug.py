#!/usr/bin/env python3
"""
DEBUG SCRIPT — Test loop step by step with detailed logging.

This script tests:
1. Customer script generation (Gemini)
2. Agent health check (ElevenLabs)
3. Full conversation simulation (1 test scenario)
4. Evaluation of result
5. Log file generation

Run: python test_loop_debug.py
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Configure VERBOSE logging to both console and file
LOG_FILE = Path(__file__).parent / "logs" / "debug_test.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(name)-20s] %(levelname)-8s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("DEBUG_TEST")

# Import after logging is configured
from refinement_loop.config import ELEVENLABS_AGENT_ID, GOOGLE_API_KEY, ELEVENLABS_API_KEY
from refinement_loop.scenarios import SCENARIOS
from refinement_loop.simulator import generate_customer_script, simulate
from refinement_loop.evaluator import evaluate_all


async def test_config():
    """Step 1: Check config."""
    logger.info("=" * 80)
    logger.info("STEP 1: CONFIGURATION CHECK")
    logger.info("=" * 80)
    
    logger.info(f"ELEVENLABS_AGENT_ID: {'✓ SET' if ELEVENLABS_AGENT_ID else '✗ NOT SET'}")
    logger.info(f"ELEVENLABS_API_KEY: {'✓ SET' if ELEVENLABS_API_KEY else '✗ NOT SET'}")
    logger.info(f"GOOGLE_API_KEY: {'✓ SET' if GOOGLE_API_KEY else '✗ NOT SET'}")
    
    if not ELEVENLABS_AGENT_ID:
        logger.error("ELEVENLABS_AGENT_ID is required. Set it in .env or environment.")
        return False
    
    return True


async def test_customer_script():
    """Step 2: Generate customer script."""
    logger.info("=" * 80)
    logger.info("STEP 2: GENERATE CUSTOMER SCRIPT (using Gemini)")
    logger.info("=" * 80)
    
    scenario = SCENARIOS[0]  # Use first scenario
    logger.info(f"Testing scenario: {scenario.id}")
    logger.info(f"Goal: {scenario.customer_goal}")
    logger.info(f"Info: {scenario.customer_info}")
    
    try:
        utterances = generate_customer_script(scenario)
        logger.info(f"✓ Generated {len(utterances)} customer utterances:")
        for i, u in enumerate(utterances, 1):
            logger.info(f"  {i}. {u}")
        return utterances
    except Exception as e:
        logger.exception(f"✗ Failed to generate customer script: {e}")
        return None


async def test_agent_health():
    """Step 3: Check agent health."""
    logger.info("=" * 80)
    logger.info("STEP 3: CHECK ELEVENLABS AGENT HEALTH")
    logger.info("=" * 80)
    
    try:
        from refinement_loop.elevenlabs_client import check_agent_health
        
        healthy = await check_agent_health()
        if healthy:
            logger.info("✓ Agent is healthy and responding")
            return True
        else:
            logger.error("✗ Agent is not responding")
            return False
    except Exception as e:
        logger.exception(f"✗ Health check failed: {e}")
        return False


async def test_conversation():
    """Step 4: Run a full conversation."""
    logger.info("=" * 80)
    logger.info("STEP 4: RUN FULL CONVERSATION SIMULATION")
    logger.info("=" * 80)
    
    scenario = SCENARIOS[0]
    
    # Load the default system prompt
    from refinement_loop.loop import RefinementLoop
    system_prompt = RefinementLoop._load_prompt()
    
    logger.info(f"System prompt (first 200 chars):\n{system_prompt[:200]}...")
    
    try:
        transcript = await simulate(scenario, system_prompt)
        logger.info(f"✓ Conversation completed")
        logger.info(f"  Scenario: {transcript.scenario_id}")
        logger.info(f"  Total turns: {len(transcript.turns)}")
        
        if transcript.turns:
            logger.info(f"\n  Transcript:")
            for i, turn in enumerate(transcript.turns, 1):
                role = turn.role.upper()
                content = turn.content[:100] + ("..." if len(turn.content) > 100 else "")
                logger.info(f"    Turn {i} [{role}]: {content}")
            return transcript
        else:
            logger.warning("✗ Conversation produced 0 turns!")
            return None
    except Exception as e:
        logger.exception(f"✗ Conversation failed: {e}")
        return None


async def test_evaluation(transcript):
    """Step 5: Evaluate the conversation."""
    logger.info("=" * 80)
    logger.info("STEP 5: EVALUATE CONVERSATION")
    logger.info("=" * 80)
    
    try:
        from refinement_loop.models import Transcript
        transcripts = [transcript] if isinstance(transcript, Transcript) else []
        
        if not transcripts or not transcripts[0].turns:
            logger.error("✗ No transcript to evaluate (empty)")
            return None
        
        evaluations = evaluate_all(transcripts, iteration=1)
        
        for eval_result in evaluations:
            logger.info(f"  Scenario: {eval_result.scenario_id}")
            logger.info(f"  Overall score: {eval_result.overall_score}")
            logger.info(f"  Passed: {eval_result.passed}")
            logger.info(f"  Root cause: {eval_result.root_cause.value}")
            
            for score in eval_result.scores:
                logger.info(f"    {score.name}: {score.score} - {score.rationale}")
        
        return evaluations
    except Exception as e:
        logger.exception(f"✗ Evaluation failed: {e}")
        return None


async def main():
    """Run all tests."""
    logger.info("=" * 80)
    logger.info("REFINEMENT LOOP DEBUG TEST")
    logger.info("=" * 80 + "\n")
    
    # Test 1: Config
    if not await test_config():
        logger.error("\n❌ CONFIG CHECK FAILED — Cannot proceed")
        return
    
    # Test 2: Customer script
    utterances = await test_customer_script()
    if not utterances:
        logger.error("\n❌ CUSTOMER SCRIPT GENERATION FAILED — Cannot proceed")
        return
    
    # Test 3: Agent health
    if not await test_agent_health():
        logger.error("\n❌ AGENT HEALTH CHECK FAILED — ElevenLabs agent is not responding")
        logger.error("   Make sure:")
        logger.error("   1. ELEVENLABS_API_KEY is set")
        logger.error("   2. ELEVENLABS_AGENT_ID is set")
        logger.error("   3. Agent exists in ElevenLabs dashboard")
        logger.error("   4. Agent is active/published")
        return
    
    # Test 4: Conversation
    transcript = await test_conversation()
    if not transcript or not transcript.turns:
        logger.error("\n❌ CONVERSATION SIMULATION FAILED — Agent did not respond")
        logger.error("   Check logs above for detailed error")
        return
    
    # Test 5: Evaluation
    evaluations = await test_evaluation(transcript)
    if not evaluations:
        logger.error("\n❌ EVALUATION FAILED")
        return
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("OK: ALL TESTS PASSED")
    logger.info("=" * 80)
    logger.info(f"\nDebug log written to: {LOG_FILE}")
    logger.info(f"Next step: Run full loop with: python start_loop.py")


if __name__ == "__main__":
    asyncio.run(main())
