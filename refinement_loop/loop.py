"""
loop.py — Autonomous refinement loop orchestrator.

Cycle:
  1. For each scenario, simulate a conversation.
  2. Evaluate all transcripts.
  3. If all pass (≥ PASS_THRESHOLD) → terminate with reason "passed".
  4. Otherwise fix (prompt and/or code) and push the updated prompt.
  5. Repeat until MAX_ITERATIONS reached → terminate with reason "max_iterations".

Broadcasts SSE events via an asyncio Queue so the observation UI can
display live progress without polling.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from refinement_loop.config import (
    LOGS_DIR,
    MAX_ITERATIONS,
    PASS_THRESHOLD,
    SYSTEM_PROMPT_FILE,
)
from refinement_loop.elevenlabs_client import get_current_prompt, push_prompt
from refinement_loop.evaluator import evaluate_all
from refinement_loop.fixer import apply_fixes
from refinement_loop.models import IterationResult, RunSummary
from refinement_loop.scenarios import SCENARIOS
from refinement_loop.simulator import simulate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("loop")


class RefinementLoop:
    """
    Self-contained loop controller.

    Parameters
    ----------
    sse_queue : asyncio.Queue, optional
        If provided, the loop puts SSE event dicts onto this queue so the
        observation UI can stream them to the browser.
    scenario_ids : list[str], optional
        Subset of scenarios to run. Defaults to all 10.
    """

    def __init__(
        self,
        sse_queue: Optional[asyncio.Queue] = None,
        scenario_ids: Optional[list[str]] = None,
    ) -> None:
        self.sse_queue = sse_queue
        from refinement_loop.scenarios import SCENARIO_MAP
        if scenario_ids:
            self.scenarios = [SCENARIO_MAP[sid] for sid in scenario_ids if sid in SCENARIO_MAP]
        else:
            self.scenarios = SCENARIOS

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(self) -> RunSummary:
        """Run the full refinement loop and return a RunSummary."""
        logger.info("━" * 80)
        logger.info("🚀 REFINEMENT LOOP STARTING")
        logger.info("━" * 80)
        
        summary = RunSummary()
        current_prompt = self._load_prompt()
        summary.initial_prompt = current_prompt

        self._emit("loop_started", {
            "max_iterations": MAX_ITERATIONS,
            "pass_threshold": PASS_THRESHOLD,
            "scenario_count": len(self.scenarios),
        })
        logger.info("✅ Initialized: %d scenarios, max %d iterations, threshold %.1f", 
                   len(self.scenarios), MAX_ITERATIONS, PASS_THRESHOLD)

        for iteration in range(1, MAX_ITERATIONS + 1):
            logger.info("━" * 80)
            logger.info("🔄 ITERATION %d / %d", iteration, MAX_ITERATIONS)
            logger.info("━" * 80)
            iter_result = IterationResult(
                iteration=iteration,
                prompt_before=current_prompt,
            )

            # ── Step 1: Simulate ─────────────────────────────────────────────
            logger.info("📝 Step 1/4: SIMULATE - Running %d scenarios...", len(self.scenarios))
            self._emit("step", {"iteration": iteration, "step": "simulate"})
            transcripts = await self._simulate_all(current_prompt)
            logger.info("✅ Simulation complete")

            # ── Step 2: Evaluate ─────────────────────────────────────────────
            logger.info("📊 Step 2/4: EVALUATE - Evaluating transcripts...")
            self._emit("step", {"iteration": iteration, "step": "evaluate"})
            evaluations = evaluate_all(transcripts, iteration)
            iter_result.evaluations = evaluations

            scores_summary = {
                e.scenario_id: {
                    "overall": round(e.overall_score, 1),
                    "passed": e.passed,
                    "root_cause": e.root_cause.value,
                }
                for e in evaluations
            }
            avg_score = sum(e.overall_score for e in evaluations) / len(evaluations)
            logger.info("📊 Evaluation complete - Average score: %.2f", avg_score)
            logger.info("  Passed: %d/%d", sum(1 for e in evaluations if e.passed), len(evaluations))
            
            self._emit("evaluation_complete", {
                "iteration": iteration,
                "scores": scores_summary,
                "average": round(avg_score, 2),
            })

            # ── Termination check ────────────────────────────────────────────
            if all(e.passed for e in evaluations):
                logger.info("🎉 SUCCESS! All scenarios passed at iteration %d", iteration)
                iter_result.prompt_after = current_prompt
                summary.iterations.append(iter_result)
                summary.terminated_reason = "passed"
                break

            if iteration == MAX_ITERATIONS:
                logger.info("⏸️  Max iterations reached")
                iter_result.prompt_after = current_prompt
                summary.iterations.append(iter_result)
                summary.terminated_reason = "max_iterations"
                break

            # ── Step 3: Fix ──────────────────────────────────────────────────
            logger.info("🔧 Step 3/4: FIX - Analyzing failures...")
            self._emit("step", {"iteration": iteration, "step": "fix"})
            new_prompt, fixes = apply_fixes(current_prompt, evaluations)
            iter_result.fixes = fixes
            logger.info("✅ Applied %d fixes", len(fixes))

            fix_descriptions = [{"type": f.fix_type, "description": f.description} for f in fixes]
            self._emit("fixes_applied", {
                "iteration": iteration,
                "fixes": fix_descriptions,
                "prompt_changed": new_prompt != current_prompt,
            })

            # ── Step 4: Push ─────────────────────────────────────────────────
            if new_prompt != current_prompt:
                logger.info("📤 Step 4/4: PUSH - Pushing updated prompt to ElevenLabs...")
                self._emit("step", {"iteration": iteration, "step": "push"})
                try:
                    await push_prompt(new_prompt)
                    logger.info("✅ Prompt pushed successfully")
                except Exception as exc:
                    logger.warning("⚠️  Failed to push prompt (continuing): %s", exc)

                self._save_prompt(new_prompt)
                iter_result.prompt_after = new_prompt
                current_prompt = new_prompt
            else:
                logger.info("⏭️  No prompt change this iteration")
                iter_result.prompt_after = current_prompt

            summary.iterations.append(iter_result)

        # ── Finalise ──────────────────────────────────────────────────────────
        summary.final_prompt = current_prompt

        log_path = self._write_log(summary)
        logger.info("━" * 80)
        logger.info("✅ LOOP COMPLETE - Reason: %s", summary.terminated_reason)
        logger.info("   Total iterations: %d", len(summary.iterations))
        logger.info("   Log file: %s", log_path)
        logger.info("━" * 80)
        
        self._emit("loop_finished", {
            "reason": summary.terminated_reason,
            "total_iterations": len(summary.iterations),
            "log_path": str(log_path),
            "final_average_score": round(
                summary.iterations[-1].average_score if summary.iterations else 0, 2
            ),
        })

        return summary

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _simulate_all(self, system_prompt: str):
        """Run simulations sequentially to respect API rate limits."""
        from refinement_loop.config import SIMULATION_DELAY_SECONDS
        from refinement_loop.models import Transcript
        
        logger.info("🎬 Running %d scenario(s) SEQUENTIALLY (one at a time)", len(self.scenarios))
        
        transcripts = []
        for i, scenario in enumerate(self.scenarios):
            if i > 0:
                # Delay between requests to respect rate limit (free tier: 5 req/min)
                logger.info("⏳ Waiting %.1fs before next scenario...", SIMULATION_DELAY_SECONDS)
                await asyncio.sleep(SIMULATION_DELAY_SECONDS)
            
            logger.info("→ Scenario %d/%d: '%s'", i+1, len(self.scenarios), scenario.id)
            
            self._emit("scenario_start", {
                "scenario_id": scenario.id,
                "scenario_name": scenario.name,
            })
            try:
                transcript = await simulate(scenario, system_prompt)
                self._emit("scenario_done", {
                    "scenario_id": scenario.id,
                    "turns": len(transcript.turns),
                })
                transcripts.append(transcript)
            except Exception as exc:
                logger.error("Simulation failed for '%s': %s", scenario.id, exc)
                # Return an empty transcript so evaluation still runs
                t = Transcript(scenario_id=scenario.id)
                transcripts.append(t)
        
        return transcripts

    def _emit(self, event: str, data: dict) -> None:
        """Put an SSE event onto the queue (non-blocking)."""
        if self.sse_queue is None:
            return
        payload = {"event": event, "data": data, "ts": _now()}
        try:
            self.sse_queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # UI too slow — drop event rather than blocking the loop

    @staticmethod
    def _load_prompt() -> str:
        if SYSTEM_PROMPT_FILE.exists():
            return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        default = _DEFAULT_PROMPT
        SYSTEM_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYSTEM_PROMPT_FILE.write_text(default, encoding="utf-8")
        return default

    @staticmethod
    def _save_prompt(prompt: str) -> None:
        SYSTEM_PROMPT_FILE.parent.mkdir(parents=True, exist_ok=True)
        SYSTEM_PROMPT_FILE.write_text(prompt, encoding="utf-8")

    @staticmethod
    def _write_log(summary: RunSummary) -> Path:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = LOGS_DIR / f"run_{timestamp}.json"
        summary.write_log(log_path)
        logger.info("Log written to %s", log_path)
        return log_path


# ── Default baseline system prompt ────────────────────────────────────────────

_DEFAULT_PROMPT = """\
You are a friendly and professional customer service agent for TechMellon Airlines.
You assist customers over the phone with bookings, queries, and requests.

You have access to the following tools via webhooks:
- Search available flights by destination, date, or price
- Book a flight for a customer
- Retrieve, reschedule, or cancel an existing booking
- Add baggage or special items to a booking
- Add special assistance requests to a booking
- Query flight status and check-in information
- Answer policy questions about pets, baggage, and refunds

Guidelines:
- Always confirm the customer's name and booking reference before modifying any booking.
- Confirm every completed action clearly (booking reference, price, new flight details).
- If a customer asks a policy question, answer it before asking if they want to book.
- Be concise but warm. Aim for calls under 5 minutes.
- End each call by asking if there is anything else you can help with.
- Never make up data. If you cannot find a flight or booking, say so clearly.
"""


def _now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the refinement loop")
    parser.add_argument(
        "--scenarios", nargs="*",
        help="Scenario IDs to run (default: all)",
    )
    parser.add_argument(
        "--max-iterations", type=int, default=MAX_ITERATIONS,
    )
    parser.add_argument(
        "--pass-threshold", type=float, default=PASS_THRESHOLD,
    )
    args = parser.parse_args()

    # Override configurable constants from CLI
    import refinement_loop.config as cfg
    cfg.MAX_ITERATIONS = args.max_iterations
    cfg.PASS_THRESHOLD = args.pass_threshold

    loop = RefinementLoop(scenario_ids=args.scenarios)
    summary = asyncio.run(loop.run())

    print(f"\nTerminated: {summary.terminated_reason}")
    print(f"Iterations: {len(summary.iterations)}")
    if summary.iterations:
        print(f"Initial avg score: {summary.iterations[0].average_score:.1f}")
        print(f"Final avg score:   {summary.iterations[-1].average_score:.1f}")
