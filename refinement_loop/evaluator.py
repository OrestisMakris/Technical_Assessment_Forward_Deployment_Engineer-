"""
Evaluator: scores a conversation transcript against four criteria and
classifies the root cause of any failures as PROMPT or CODE.

Scoring criteria (1–10 each):
  1. understanding   — Did the agent correctly understand the customer's request?
  2. api_usage       — Was the right API called with correct parameters?
  3. confirmation    — Was the outcome confirmed clearly to the customer?
  4. naturalness     — Was the call handled naturally end-to-end?

Root cause taxonomy:
  PROMPT — agent misunderstood, gave wrong policy info, ignored instructions,
            or was poorly guided by the system prompt.
  CODE   — an API returned wrong data, a webhook misfired, a booking failed
            to persist, logic was incorrect.
  BOTH   — failures span both layers (needs both fixes).
  NONE   — no failures, all criteria pass.
"""

from __future__ import annotations

import json
import logging
import os

import google.generativeai as genai

from refinement_loop.config import EVALUATOR_MODEL, GOOGLE_API_KEY
from refinement_loop.models import (
    CriterionScore,
    EvaluationResult,
    RootCause,
    Transcript,
)
from refinement_loop.scenarios import Scenario, SCENARIO_MAP

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


# ── Evaluation prompt ─────────────────────────────────────────────────────────

_EVAL_SYSTEM = """\
You are an expert quality evaluator for airline customer service AI agents.
You will receive a conversation transcript and the scenario the customer was trying to achieve.

Score the agent on EXACTLY these four criteria, each from 1 to 10:
  1. understanding   — Did the agent correctly identify and respond to the customer's core request?
  2. api_usage       — Were the correct backend operations performed with correct parameters?
                       (infer from agent's responses; if it gave wrong data or failed to
                        book/cancel/modify, score accordingly)
  3. confirmation    — Did the agent clearly confirm the outcome (booking ref, refund amount,
                        policy detail) to the customer?
  4. naturalness     — Did the conversation flow naturally? Was the agent helpful, polite,
                       and concise without being robotic?

Then classify the root cause of any failures:
  "prompt" — the agent misunderstood, gave wrong policy, or was poorly instructed
  "code"   — an API call failed, returned wrong data, or a booking was not persisted
  "both"   — failures span both layers
  "none"   — no failures (all scores ≥ 8)

If root_cause is "code" or "both", identify:
  - faulty_file: the most likely source file (e.g. "backend/routes/bookings.py")
  - faulty_behaviour: a one-sentence description of what is wrong

Respond with ONLY a JSON object matching this schema (no markdown, no extra text):
{
  "scores": {
    "understanding": {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": "<exact agent quote that failed, or empty>"},
    "api_usage":     {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": ""},
    "confirmation":  {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": ""},
    "naturalness":   {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": ""}
  },
  "root_cause": "prompt|code|both|none",
  "root_cause_explanation": "<≤60 words explaining why>",
  "faulty_file": "<filepath or null>",
  "faulty_behaviour": "<one sentence or null>"
}
"""

_EVAL_USER = """\
SCENARIO
--------
Name: {scenario_name}
Customer goal: {customer_goal}
Expected APIs to be called: {expected_apis}

TRANSCRIPT
----------
{transcript}
"""


def evaluate(
    transcript: Transcript,
    iteration: int,
) -> EvaluationResult:
    """
    Score a transcript and classify root cause.
    Returns an EvaluationResult.
    """
    scenario = SCENARIO_MAP.get(transcript.scenario_id)
    if scenario is None:
        raise ValueError(f"Unknown scenario_id: {transcript.scenario_id!r}")

    # Handle empty transcripts (simulation failed)
    if not transcript.turns:
        logger.warning(
            "Empty transcript for '%s' - simulation failed, returning low scores",
            transcript.scenario_id,
        )
        return EvaluationResult(
            scenario_id=transcript.scenario_id,
            iteration=iteration,
            scores=[
                CriterionScore(
                    name="understanding",
                    score=0.0,
                    rationale="No transcript available - simulation failed",
                    failure_quote="",
                ),
                CriterionScore(
                    name="api_usage",
                    score=0.0,
                    rationale="No transcript available - simulation failed",
                    failure_quote="",
                ),
                CriterionScore(
                    name="confirmation",
                    score=0.0,
                    rationale="No transcript available - simulation failed",
                    failure_quote="",
                ),
                CriterionScore(
                    name="naturalness",
                    score=0.0,
                    rationale="No transcript available - simulation failed",
                    failure_quote="",
                ),
            ],
            root_cause=RootCause.INSUFFICIENT_INFO,
            root_cause_explanation="Simulation failed - ElevenLabs WebSocket connection timeout",
            faulty_file=None,
            faulty_behaviour=None,
        )

    user_msg = _EVAL_USER.format(
        scenario_name=scenario.name,
        customer_goal=scenario.customer_goal,
        expected_apis=", ".join(scenario.expected_apis),
        transcript=transcript.as_text(),
    )

    model = genai.GenerativeModel(
        model_name=EVALUATOR_MODEL,
        system_instruction=_EVAL_SYSTEM,
    )
    resp = model.generate_content(
        user_msg,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=1024,
        ),
    )

    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)

    scores = []
    for name in ("understanding", "api_usage", "confirmation", "naturalness"):
        s = data["scores"][name]
        scores.append(CriterionScore(
            name=name,
            score=float(s["score"]),
            rationale=s["rationale"],
            failure_quote=s.get("failure_quote", ""),
        ))

    root_cause = RootCause(data["root_cause"])

    result = EvaluationResult(
        scenario_id=transcript.scenario_id,
        iteration=iteration,
        scores=scores,
        root_cause=root_cause,
        root_cause_explanation=data["root_cause_explanation"],
        faulty_file=data.get("faulty_file"),
        faulty_behaviour=data.get("faulty_behaviour"),
    )

    logger.info(
        "Eval '%s' iter %d: %.1f/10 (root cause: %s)",
        transcript.scenario_id,
        iteration,
        result.overall_score,
        root_cause.value,
    )
    return result


def evaluate_all(
    transcripts: list[Transcript],
    iteration: int,
) -> list[EvaluationResult]:
    """Evaluate a batch of transcripts, one per scenario."""
    return [evaluate(t, iteration) for t in transcripts]
