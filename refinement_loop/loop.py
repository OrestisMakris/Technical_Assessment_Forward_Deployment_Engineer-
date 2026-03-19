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
        summary = RunSummary()
        current_prompt = self._load_prompt()
        summary.initial_prompt = current_prompt

        self._emit("loop_started", {
            "max_iterations": MAX_ITERATIONS,
            "pass_threshold": PASS_THRESHOLD,
            "scenario_count": len(self.scenarios),
        })

        for iteration in range(1, MAX_ITERATIONS + 1):
            logger.info("═══ ITERATION %d / %d ═══", iteration, MAX_ITERATIONS)
            iter_result = IterationResult(
                iteration=iteration,
                prompt_before=current_prompt,
            )

            # ── Step 1: Simulate ─────────────────────────────────────────────
            self._emit("step", {"iteration": iteration, "step": "simulate"})
            transcripts = await self._simulate_all(current_prompt)

            # ── Step 2: Evaluate ─────────────────────────────────────────────
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
            self._emit("evaluation_complete", {
                "iteration": iteration,
                "scores": scores_summary,
                "average": round(
                    sum(e.overall_score for e in evaluations) / len(evaluations), 2
                ),
            })

            # ── Termination check ────────────────────────────────────────────
            if all(e.passed for e in evaluations):
                logger.info("All scenarios passed at iteration %d — terminating.", iteration)
                iter_result.prompt_after = current_prompt
                summary.iterations.append(iter_result)
                summary.terminated_reason = "passed"
                break

            if iteration == MAX_ITERATIONS:
                logger.info("Max iterations reached — terminating.")
                iter_result.prompt_after = current_prompt
                summary.iterations.append(iter_result)
                summary.terminated_reason = "max_iterations"
                break

            # ── Step 3: Fix ──────────────────────────────────────────────────
            self._emit("step", {"iteration": iteration, "step": "fix"})
            new_prompt, fixes = apply_fixes(current_prompt, evaluations)
            iter_result.fixes = fixes

            fix_descriptions = [{"type": f.fix_type, "description": f.description} for f in fixes]
            self._emit("fixes_applied", {
                "iteration": iteration,
                "fixes": fix_descriptions,
                "prompt_changed": new_prompt != current_prompt,
            })

            # ── Step 4: Push ─────────────────────────────────────────────────
            if new_prompt != current_prompt:
                self._emit("step", {"iteration": iteration, "step": "push"})
                try:
                    await push_prompt(new_prompt)
                    logger.info("Prompt pushed to ElevenLabs.")
                except Exception as exc:
                    logger.warning("Failed to push prompt (continuing anyway): %s", exc)

                self._save_prompt(new_prompt)
                iter_result.prompt_after = new_prompt
                current_prompt = new_prompt
            else:
                iter_result.prompt_after = current_prompt
                logger.info("No prompt change this iteration.")

            summary.iterations.append(iter_result)

        # ── Finalise ──────────────────────────────────────────────────────────
        summary.final_prompt = current_prompt

        log_path = self._write_log(summary)
        self._emit("loop_finished", {
            "reason": summary.terminated_reason,
            "total_iterations": len(summary.iterations),
            "log_path": str(log_path),
            "final_average_score": round(
                summary.iterations[-1].average_score if summary.iterations else 0, 2
            ),
        })

        logger.info(
            "Run complete. Reason: %s. Iterations: %d.",
            summary.terminated_reason,
            len(summary.iterations),
        )
        return summary

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _simulate_all(self, system_prompt: str):
        """Run simulations for all scenarios concurrently (bounded)."""
        sem = asyncio.Semaphore(3)  # max 3 concurrent ElevenLabs sessions

        async def _run_one(scenario):
            async with sem:
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
                    return transcript
                except Exception as exc:
                    logger.error("Simulation failed for '%s': %s", scenario.id, exc)
                    # Return an empty transcript so evaluation still runs
                    from refinement_loop.models import Transcript
                    t = Transcript(scenario_id=scenario.id)
                    return t

        tasks = [_run_one(s) for s in self.scenarios]
        return await asyncio.gather(*tasks)

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
