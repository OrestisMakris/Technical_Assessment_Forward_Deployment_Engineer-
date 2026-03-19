"""
ElevenLabs Conversational AI client.

Covers two responsibilities:
  1. Agent management — read and update the system prompt via REST API.
  2. Text-mode conversation — run a multi-turn dialogue using the
     ElevenLabs Conversational AI WebSocket in text mode.

ElevenLabs WS protocol (text mode):
  - Connect to wss://api.elevenlabs.io/v1/convai/conversation?agent_id=<id>
  - Send: {"type": "conversation_initiation_client_data", "conversation_config_override": {...}}
  - Then alternate:
      send:    {"user_audio_chunk": <base64 silence>}  OR  use text injection
      receive: {"type": "agent_response", "agent_response_event": {"agent_response": "..."}}
  ElevenLabs' text injection uses:
      send: {"type": "user_turn", "user_turn": {"text": "..."}}
  We use this path so no audio codec is needed.
"""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
import websockets

from refinement_loop.config import (
    ELEVENLABS_AGENT_ID,
    ELEVENLABS_API_KEY,
    MAX_CONVERSATION_TURNS,
)
from refinement_loop.models import ConversationTurn, Transcript

logger = logging.getLogger(__name__)

_BASE = "https://api.elevenlabs.io/v1"
_HEADERS = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json",
}


# ── Agent management ──────────────────────────────────────────────────────────

async def get_current_prompt() -> str:
    """Fetch the agent's current system prompt."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{_BASE}/convai/agents/{ELEVENLABS_AGENT_ID}",
            headers=_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["conversation_config"]["agent"]["prompt"]["prompt"]


async def check_agent_health() -> bool:
    """
    Check if the ElevenLabs agent is reachable and responding.
    Returns True if agent is healthy, False otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{_BASE}/convai/agents/{ELEVENLABS_AGENT_ID}",
                headers=_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
            # Check if agent has required configuration
            is_healthy = (
                data.get("conversation_config") is not None and
                data.get("conversation_config", {}).get("agent") is not None
            )
            if is_healthy:
                logger.info("✅ ElevenLabs agent %s is healthy", ELEVENLABS_AGENT_ID)
            else:
                logger.warning("⚠️ ElevenLabs agent %s configuration incomplete", ELEVENLABS_AGENT_ID)
            return is_healthy
    except Exception as e:
        logger.error("❌ ElevenLabs agent health check failed: %s", e)
        return False


async def push_prompt(new_prompt: str) -> None:
    """Update the agent's system prompt via the ElevenLabs REST API."""
    payload = {
        "conversation_config": {
            "agent": {
                "prompt": {"prompt": new_prompt}
            }
        }
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            f"{_BASE}/convai/agents/{ELEVENLABS_AGENT_ID}",
            headers=_HEADERS,
            json=payload,
        )
        resp.raise_for_status()
    logger.info("Prompt pushed to ElevenLabs agent %s", ELEVENLABS_AGENT_ID)


# ── Text-mode conversation ────────────────────────────────────────────────────

_WS_URL = (
    f"wss://api.elevenlabs.io/v1/convai/conversation"
    f"?agent_id={ELEVENLABS_AGENT_ID}"
)


async def _send_user_turn(ws, text: str) -> None:
    """Inject a customer utterance as text into the ElevenLabs WS session."""
    logger.info("Sending user turn: %s", text[:60])
    await ws.send(json.dumps({
        "type": "user_turn",
        "user_turn": {"text": text},
    }))


async def _drain_stale_frames(ws, max_wait_seconds: float = 0.4) -> None:
    """Best-effort drain of queued non-content frames between turns."""
    end_at = asyncio.get_running_loop().time() + max_wait_seconds
    drained = 0
    while asyncio.get_running_loop().time() < end_at:
        timeout = max(0.01, end_at - asyncio.get_running_loop().time())
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            break
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        msg_type = msg.get("type", "")
        # Keep only transport/control out of the queue.
        if msg_type in {"ping", "audio", "audio_burst", "turn_started", "turn_start", "user_turn_finished"}:
            drained += 1
            continue
        # If we see a substantive message, stop draining and let normal flow handle it.
        break
    if drained:
        logger.debug("Drained %d stale frame(s) before next turn", drained)


async def _consume_initial_greeting(ws) -> str:
    """
    Consume the automatic greeting emitted by ElevenLabs after handshake.
    This prevents greeting tail audio from leaking into turn 1/2 alignment.
    
    Greeting comes as: agent_chat_response_part frames (0-3) then agent_response event.
    """
    import time
    greeting = ""
    start_time = time.time()
    frame_count = 0
    
    try:
        while time.time() - start_time < 15.0:  # 15 second total timeout
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                frame_count += 1
                msg = json.loads(raw)
                msg_type = msg.get("type", "")
                
                # Look for the greeting in agent_response event
                if msg_type == "agent_response":
                    greeting = msg.get("agent_response_event", {}).get("agent_response", "")
                    if greeting:
                        logger.info("✅ Initial greeting: %s", greeting[:80])
                        return greeting
                
                # Skip these frames but don't give up
                elif msg_type in ("agent_chat_response_part", "ping", "conversation_initiation_metadata", "audio"):
                    if msg_type == "agent_chat_response_part":
                        logger.debug("Agent building response (frame %d)", frame_count)
                    continue
                
                else:
                    logger.debug("Greeting frame type: %s (frame %d)", msg_type, frame_count)
            
            except asyncio.TimeoutError:
                # Per-message timeout - keep looping
                continue
    
    except Exception as e:
        logger.warning("Error consuming greeting: %s", e)
    
    if not greeting:
        logger.warning("No initial greeting received after %d frames", frame_count)
    
    return greeting


async def _receive_agent_response(ws) -> str:
    """
    Wait for the agent response to a customer message.
    
    ElevenLabs sends:
    - agent_chat_response_part (0-3 frames, building the response)
    - agent_response event (full final text)
    
    Strategy:
    - Ignore agent_chat_response_part frames
    - Grab the agent_response event text
    - Timeout after 30 seconds of listening
    """
    import time
    
    agent_response_text = ""
    start_time = time.time()
    frame_count = 0
    max_wait = 30.0  # seconds
    
    try:
        while time.time() - start_time < max_wait:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                msg = json.loads(raw)
                msg_type = msg.get("type", "")
                frame_count += 1

                # AGENT RESPONSE EVENT (full text)
                if msg_type == "agent_response":
                    text = msg.get("agent_response_event", {}).get("agent_response", "")
                    if text:
                        agent_response_text = text
                        logger.info("✅ Response (frame %d): %s", frame_count, text[:100])
                        return agent_response_text
                
                # Skip these but keep listening
                elif msg_type in ("agent_chat_response_part", "ping", "audio"):
                    logger.debug("Frame %d: %s (skipping)", frame_count, msg_type)
                    continue
                
                else:
                    logger.debug("Frame %d: %s", frame_count, msg_type)
            
            except asyncio.TimeoutError:
                # Per-recv timeout - keep trying
                continue
    
    except Exception as e:
        logger.error("Error in _receive_agent_response: %s", e)
    
    if not agent_response_text:
        logger.warning("❌ No response received after %d frames in %.1fs", frame_count, time.time() - start_time)
    
    return agent_response_text


async def run_conversation(customer_turns: list[str]) -> Transcript:
    """
    Run a full conversation against the ElevenLabs agent in text mode.

    customer_turns is produced externally by the simulator; this function
    sends them one at a time and collects the agent's replies.

    Returns a Transcript with interleaved customer/agent turns.
    """
    transcript = Transcript(scenario_id="")   # caller sets scenario_id
    extra_headers = {"xi-api-key": ELEVENLABS_API_KEY}

    # Retry logic with exponential backoff (up to 3 attempts)
    max_retries = 3
    retry_delay = 2.0
    ws = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Attempting ElevenLabs connection (attempt %d/%d)", attempt, max_retries)
            
            # Connection timeout: 30 seconds (allows for slower networks)
            async with asyncio.timeout(30.0):
                ws = await websockets.connect(_WS_URL, additional_headers=extra_headers)
            
            logger.info("✅ ElevenLabs WebSocket connection established")
            break
            
        except (asyncio.TimeoutError, TimeoutError) as e:
            logger.warning("Connection attempt %d failed: timeout", attempt)
            if attempt < max_retries:
                logger.info("Retrying in %.1fs...", retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay *= 1.5  # exponential backoff
            else:
                logger.error("Failed to connect after %d attempts", max_retries)
                raise TimeoutError(f"Failed to connect to ElevenLabs after {max_retries} attempts") from e
        except Exception as e:
            logger.error("Connection failed: %s", e)
            if attempt < max_retries:
                logger.info("Retrying in %.1fs...", retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                raise

    if not ws:
        raise RuntimeError("Failed to establish WebSocket connection")

    async with ws:
        # Handshake — TEXT MODE with explicit configuration
        logger.debug("Sending text-mode handshake...")
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "agent": {
                    "enable_model_fallback": False,
                },
                "client_tool_result": {
                    "notification_level": "silent",
                },
            },
        }))

        # Discard the initiation response (with timeout)
        try:
            init_resp = await asyncio.wait_for(ws.recv(), timeout=10.0)
            logger.debug("Received handshake response")
        except asyncio.TimeoutError:
            logger.warning("No handshake response from agent (continuing anyway)")

        # Sync with ElevenLabs automatic greeting before user-turn injection.
        # This avoids cross-turn frame leakage like trailing "you today".
        _ = await _consume_initial_greeting(ws)
        await _drain_stale_frames(ws)

        # Run conversation (per-message timeouts only)
        num_turns = len(customer_turns[:MAX_CONVERSATION_TURNS])
        logger.info("Starting text-mode conversation with %d customer turns", num_turns)
        
        for i, user_text in enumerate(customer_turns[:MAX_CONVERSATION_TURNS]):
            turn_num = i + 1
            logger.info("━" * 60)
            logger.info("Turn %d/%d: CUSTOMER", turn_num, num_turns)
            logger.info("  %s", user_text if len(user_text) < 80 else user_text[:80] + "...")
            transcript.turns.append(ConversationTurn(role="customer", content=user_text))
            
            try:
                await _drain_stale_frames(ws)
                # Send user turn in correct format
                await _send_user_turn(ws, user_text)
            except Exception as e:
                logger.error("Failed to send user turn %d: %s", turn_num, e)
                break
            
            # Small delay to let agent process (avoid overwhelming)
            await asyncio.sleep(0.3)

            # Per-message timeout: 25 seconds for agent response (ElevenLabs can be slow)
            agent_text = ""
            try:
                logger.info("Waiting for agent response (timeout: 25s)...")
                agent_text = await asyncio.wait_for(
                    _receive_agent_response(ws), timeout=25.0
                )
            except asyncio.TimeoutError:
                logger.warning("⏱️  Agent response timeout for turn %d (waiting 30s more)", turn_num)
                # Try once more with longer timeout
                try:
                    agent_text = await asyncio.wait_for(
                        _receive_agent_response(ws), timeout=30.0
                    )
                except asyncio.TimeoutError:
                    logger.error("❌ Agent failed to respond on turn %d (30s timeout exceeded)", turn_num)
                    break

            if agent_text:
                logger.info("Turn %d/%d: AGENT", turn_num, num_turns)
                logger.info("  %s", agent_text if len(agent_text) < 80 else agent_text[:80] + "...")
                transcript.turns.append(ConversationTurn(role="agent", content=agent_text))
            else:
                logger.warning("❌ Turn %d: Agent returned empty response", turn_num)
                # Optionally continue or break
                if i < num_turns - 1:
                    logger.info("Continuing to next turn...")
                else:
                    logger.info("Last turn had empty response, ending conversation")
                    break

            # Small gap between turns to avoid overlap with trailing transport
            # frames and give ElevenLabs time to fully switch back to listening.
            await asyncio.sleep(0.5)

            # If agent signals end of call, stop early
            end_phrases = ("is there anything else", "goodbye", "have a great flight", "thank you!", "you're all set")
            if agent_text and any(p in agent_text.lower() for p in end_phrases):
                logger.info("🎯 Agent signaled end of conversation with: %s", agent_text[:50])
                break

        logger.info("━" * 60)
        logger.info("Conversation complete: %d turns captured", len(transcript.turns))
        
        # Politely end the session
        try:
            await ws.send(json.dumps({"type": "end_conversation"}))
            logger.debug("Sent end_conversation signal")
        except Exception as e:
            logger.debug("Error sending end signal: %s", e)

    return transcript


# ── Fallback: direct prompt mode (for testing without ElevenLabs creds) ──────

async def run_conversation_fallback(
    customer_turns: list[str],
    system_prompt: str,
    anthropic_client,
) -> Transcript:
    """
    When ELEVENLABS_AGENT_ID is not set or the WS fails, simulate the agent
    using Claude directly with the current system prompt. Useful for local dev.
    """
    import anthropic as sdk

    transcript = Transcript(scenario_id="")
    messages: list[dict] = []

    for user_text in customer_turns[:MAX_CONVERSATION_TURNS]:
        transcript.turns.append(ConversationTurn(role="customer", content=user_text))
        messages.append({"role": "user", "content": user_text})

        resp = anthropic_client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=512,
            system=system_prompt,
            messages=messages,
        )
        agent_text = resp.content[0].text
        transcript.turns.append(ConversationTurn(role="agent", content=agent_text))
        messages.append({"role": "assistant", "content": agent_text})

        end_phrases = ("is there anything else", "goodbye", "have a great flight")
        if any(p in agent_text.lower() for p in end_phrases):
            break

    return transcript
