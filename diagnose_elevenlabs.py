#!/usr/bin/env python3
"""
DIAGNOSTIC SCRIPT — Check ElevenLabs configuration and connection.

Run this to verify:
1. API keys are set correctly
2. Agent exists and is active
3. WebSocket can connect
4. Agent can receive text messages
5. Agent can respond
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Setup logging
LOG_FILE = Path(__file__).parent / "logs" / "diagnostic.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("DIAGNOSTIC")

import httpx
from refinement_loop.config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_AGENT_ID,
    GOOGLE_API_KEY,
)


def check_env_vars():
    """Check that all required environment variables are set."""
    logger.info("=" * 80)
    logger.info("CHECKING ENVIRONMENT VARIABLES")
    logger.info("=" * 80)
    
    checks = [
        ("ELEVENLABS_API_KEY", bool(ELEVENLABS_API_KEY)),
        ("ELEVENLABS_AGENT_ID", bool(ELEVENLABS_AGENT_ID)),
        ("GOOGLE_API_KEY", bool(GOOGLE_API_KEY)),
    ]
    
    all_ok = True
    for name, is_set in checks:
        status = "✓ SET" if is_set else "✗ NOT SET"
        logger.info(f"{name:30} {status}")
        if not is_set:
            all_ok = False
    
    return all_ok


async def check_agent_exists():
    """Check that the agent exists on ElevenLabs."""
    logger.info("\n" + "=" * 80)
    logger.info("CHECKING AGENT EXISTS (REST API)")
    logger.info("=" * 80)
    
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID:
        logger.error("Cannot check agent without API key and agent ID")
        return False
    
    url = f"https://api.elevenlabs.io/v1/convai/agents/{ELEVENLABS_AGENT_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers)
            
            if resp.status_code == 200:
                agent = resp.json()
                logger.info(f"✓ Agent exists")
                logger.info(f"  Name: {agent.get('name', 'N/A')}")
                logger.info(f"  Status: {agent.get('status', 'N/A')}")
                logger.info(f"  Created: {agent.get('created_at', 'N/A')}")
                return True
            elif resp.status_code == 401:
                logger.error("✗ Unauthorized (invalid API key?)")
                return False
            elif resp.status_code == 404:
                logger.error("✗ Agent not found (invalid agent ID?)")
                logger.error(f"  Agent ID: {ELEVENLABS_AGENT_ID}")
                return False
            else:
                logger.error(f"✗ HTTP {resp.status_code}: {resp.text}")
                return False
    
    except Exception as e:
        logger.exception(f"✗ Error checking agent: {e}")
        return False


async def check_ws_connection():
    """Try to connect to the WebSocket."""
    logger.info("\n" + "=" * 80)
    logger.info("CHECKING WEBSOCKET CONNECTION")
    logger.info("=" * 80)
    
    if not ELEVENLABS_API_KEY or not ELEVENLABS_AGENT_ID:
        logger.error("Cannot check WebSocket without API key and agent ID")
        return False
    
    ws_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY}
    
    try:
        import websockets
        
        logger.info(f"Connecting to: {ws_url}")
        
        async with asyncio.timeout(15.0):
            ws = await websockets.connect(ws_url, additional_headers=headers)
        
        logger.info("✓ WebSocket connection successful")
        
        # Try to send handshake
        logger.info("Sending handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {"enable_model_fallback": False},
                "client_tool_result": {"notification_level": "silent"},
            },
        }))
        
        # Try to receive response
        logger.info("Waiting for handshake response (timeout: 5s)...")
        try:
            resp = await asyncio.wait_for(ws.recv(), timeout=5.0)
            logger.info("✓ Received handshake response")
            logger.info(f"  Response type: {json.loads(resp).get('type', 'unknown')}")
        except asyncio.TimeoutError:
            logger.warning("⏱️  No handshake response (continuing anyway)")
        
        # Try to send a test message
        logger.info("\nSending test message: 'Hello'")
        await ws.send(json.dumps({
            "type": "user_turn",
            "user_turn": {"text": "Hello"},
        }))
        
        # Try to receive agent response (with timeout)
        logger.info("Waiting for agent response (timeout: 15s)...")
        received_response = False
        start = asyncio.get_running_loop().time()
        
        while asyncio.get_running_loop().time() - start < 15.0:
            try:
                timeout = 1.0
                raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
                msg = json.loads(raw)
                
                if msg.get("type") == "agent_response":
                    agent_text = msg.get("agent_response_event", {}).get("agent_response", "")
                    if agent_text:
                        logger.info(f"✓ Agent responded: {agent_text[:100]}")
                        received_response = True
                        break
                else:
                    logger.debug(f"Got frame type: {msg.get('type')}")
            
            except asyncio.TimeoutError:
                continue
        
        if not received_response:
            logger.warning("⏱️  Agent did not respond within 15 seconds")
            return False
        
        await ws.close()
        return True
    
    except Exception as e:
        logger.exception(f"✗ WebSocket connection failed: {e}")
        return False


async def main():
    """Run all diagnostic checks."""
    logger.info("\n" + "=" * 80)
    logger.info("ELEVENLABS DIAGNOSTIC CHECK")
    logger.info("=" * 80 + "\n")
    
    # Check 1: Environment variables
    if not check_env_vars():
        logger.error("\n❌ Some environment variables are missing")
        logger.error("   Set them in .env or export them:")
        logger.error("   export ELEVENLABS_API_KEY=<key>")
        logger.error("   export ELEVENLABS_AGENT_ID=<id>")
        logger.error("   export GOOGLE_API_KEY=<key>")
        return
    
    logger.info("✓ All environment variables are set\n")
    
    # Check 2: Agent exists
    if not await check_agent_exists():
        logger.error("\n❌ Agent check failed")
        return
    
    # Check 3: WebSocket connection
    if not await check_ws_connection():
        logger.error("\n❌ WebSocket check failed")
        logger.error("   The agent may not be published or enabled")
        return
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL DIAGNOSTIC CHECKS PASSED")
    logger.info("=" * 80)
    logger.info(f"\nNext step: Run the loop")
    logger.info(f"  python start_loop.py")
    logger.info(f"\nDiagnostic log saved to: {LOG_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
