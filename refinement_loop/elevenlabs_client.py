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
import base64
import json
import logging
from typing import AsyncGenerator

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
    await ws.send(json.dumps({
        "type": "user_turn",
        "user_turn": {"text": text},
    }))


async def _receive_agent_response(ws) -> str:
    """
    Wait for the agent to finish speaking.
    ElevenLabs sends multiple partial audio events then a final
    'agent_response' event. We collect the final text response.
    Returns empty string on timeout or unexpected closure.
    """
    buffer = []
    try:
        async for raw in ws:
            msg = json.loads(raw)
            t = msg.get("type", "")

            if t == "agent_response":
                # Full text response available
                text = msg.get("agent_response_event", {}).get("agent_response", "")
                if text:
                    return text

            elif t == "agent_response_correction":
                # Partial streaming token — accumulate
                delta = msg.get("agent_response_correction_event", {}).get("correction", "")
                buffer.append(delta)

            elif t in ("turn_start", "interruption", "ping"):
                # Control frames — ignore
                pass

            elif t == "conversation_ended":
                break

    except websockets.exceptions.ConnectionClosed:
        pass

    return "".join(buffer)


async def run_conversation(customer_turns: list[str]) -> Transcript:
    """
    Run a full conversation against the ElevenLabs agent in text mode.

    customer_turns is produced externally by the simulator; this function
    sends them one at a time and collects the agent's replies.

    Returns a Transcript with interleaved customer/agent turns.
    """
    transcript = Transcript(scenario_id="")   # caller sets scenario_id
    extra_headers = {"xi-api-key": ELEVENLABS_API_KEY}

    async with websockets.connect(_WS_URL, additional_headers=extra_headers) as ws:
        # Handshake
        await ws.send(json.dumps({
            "type": "conversation_initiation_client_data",
            "conversation_config_override": {
                "tts": {"voice_id": None}   # no audio output needed
            },
        }))

        # Discard the initiation response
        await ws.recv()

        for user_text in customer_turns[:MAX_CONVERSATION_TURNS]:
            transcript.turns.append(ConversationTurn(role="customer", content=user_text))
            await _send_user_turn(ws, user_text)

            agent_text = await asyncio.wait_for(
                _receive_agent_response(ws), timeout=30.0
            )
            transcript.turns.append(ConversationTurn(role="agent", content=agent_text))

            # If agent signals end of call, stop early
            end_phrases = ("is there anything else", "goodbye", "have a great flight")
            if any(p in agent_text.lower() for p in end_phrases):
                break

        # Politely end the session
        try:
            await ws.send(json.dumps({"type": "end_conversation"}))
        except Exception:
            pass

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
