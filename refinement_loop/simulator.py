"""
Simulator: an LLM plays the customer, interacting with the ElevenLabs agent.

Strategy
--------
We run two phases:

Phase 1 — pre-generate customer utterances.
  We ask Gemini to roleplay the customer and produce a realistic list of
  utterances it would make to accomplish its goal. This avoids the latency
  of interleaving two live LLM calls and makes transcripts deterministic
  (same scenario → same customer script, modulo temperature).

Phase 2 — feed those utterances into the ElevenLabs agent one by one,
  collect agent replies, and return the full transcript.

Using pre-generated turns is a conscious tradeoff: it means the customer
cannot react to surprising agent responses mid-call. For the purposes of
this assessment the coverage and consistency benefits outweigh the loss of
full interactivity. A 'reactive' mode is sketched at the bottom of this file.
"""

from __future__ import annotations

import json
import logging
import os

import google.generativeai as genai

from refinement_loop.config import CUSTOMER_MODEL, MAX_CONVERSATION_TURNS, ELEVENLABS_AGENT_ID, GOOGLE_API_KEY
from refinement_loop.models import Transcript
from refinement_loop.scenarios import Scenario

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


# ── Phase 1: generate customer script ────────────────────────────────────────

_SCRIPT_SYSTEM = """\
You are a realistic airline customer calling a customer service line.
You will be given your goal, background information, and the maximum number of
turns you can take.

Produce a JSON array of strings. Each string is one thing you would say during
the call, in order. Be natural and conversational — don't list requirements
robotically. Include realistic details like your name and booking reference
when relevant. If you need something confirmed, ask for it explicitly.

Rules:
- Produce between 3 and {max_turns} utterances.
- The LAST utterance must be a polite sign-off (e.g. "Great, thanks so much!").
- Output ONLY the JSON array, no other text, no markdown fences.
"""

_SCRIPT_USER = """\
Your goal: {goal}

Your background information: {info}

Produce the customer utterance list now.
"""


def generate_customer_script(scenario: Scenario) -> list[str]:
    """
    Ask the LLM to produce the customer's side of the conversation as a
    pre-planned list of utterances.
    """
    system = _SCRIPT_SYSTEM.format(max_turns=MAX_CONVERSATION_TURNS - 1)
    user = _SCRIPT_USER.format(
        goal=scenario.customer_goal,
        info=scenario.customer_info,
    )

    model = genai.GenerativeModel(
        model_name=CUSTOMER_MODEL,
        system_instruction=system,
    )
    resp = model.generate_content(
        user,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=1024,
        ),
    )

    raw = resp.text.strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    utterances: list[str] = json.loads(raw)
    logger.debug("Generated %d customer utterances for '%s'", len(utterances), scenario.id)
    return utterances


# ── Phase 2: run the conversation ─────────────────────────────────────────────

async def simulate(scenario: Scenario, system_prompt: str) -> Transcript:
    """
    Run a full simulated conversation for a scenario using ElevenLabs agent.

    Returns a Transcript with interleaved customer/agent turns.
    """
    customer_utterances = generate_customer_script(scenario)

    # Use ElevenLabs WebSocket agent
    if not ELEVENLABS_AGENT_ID:
        raise ValueError(
            "ELEVENLABS_AGENT_ID not configured. Cannot run simulation without ElevenLabs agent."
        )

    from refinement_loop.elevenlabs_client import run_conversation
    try:
        transcript = await run_conversation(customer_utterances)
    except Exception as exc:
        logger.error(
            "ElevenLabs WS failed: %s - %s", 
            type(exc).__name__, str(exc)
        )
        # Return empty transcript so evaluation can still run
        transcript = Transcript(scenario_id=scenario.id)

    transcript.scenario_id = scenario.id
    if transcript.turns:
        logger.info(
            "Transcript for '%s': %d turns", scenario.id, len(transcript.turns)
        )
    else:
        logger.warning(
            "Transcript for '%s': EMPTY (ElevenLabs connection failed)", scenario.id
        )
    return transcript


# ── Reactive mode (sketch) ────────────────────────────────────────────────────
# In reactive mode the customer LLM sees each agent reply and produces the
# next utterance on the fly, allowing it to react to surprising responses.
# This is more realistic but doubles latency and cost.
#
# async def simulate_reactive(scenario: Scenario, system_prompt: str) -> Transcript:
#     transcript = Transcript(scenario_id=scenario.id)
#     messages = [{"role": "user", "content": _build_reactive_prompt(scenario)}]
#
#     async for agent_reply in agent_stream(system_prompt):
#         transcript.turns.append(ConversationTurn("agent", agent_reply))
#         # Ask customer LLM what to say next given the agent reply ...
#         ...
