#!/usr/bin/env python
"""
Validate loop orchestration without ElevenLabs transport.

Checks:
- Iterative cycle executes autonomously.
- Prompt + code fixes can both occur in same iteration.
- Prompt push is invoked when prompt changed.
- Loop terminates when all scenarios pass.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from refinement_loop.loop import RefinementLoop
from refinement_loop.models import ConversationTurn, CriterionScore, EvaluationResult, Fix, RootCause, Transcript


@dataclass
class Calls:
    push_prompt: int = 0
    apply_fixes: int = 0
    evaluate_all: int = 0


async def main() -> int:
    calls = Calls()

    async def fake_simulate_all(self, system_prompt: str):
        transcripts = []
        for scenario in self.scenarios:
            transcripts.append(
                Transcript(
                    scenario_id=scenario.id,
                    turns=[
                        ConversationTurn("customer", "I need help with my booking."),
                        ConversationTurn("agent", "I can help with that."),
                    ],
                )
            )
        return transcripts

    def fake_evaluate_all(transcripts: list[Transcript], iteration: int):
        calls.evaluate_all += 1
        results: list[EvaluationResult] = []
        for t in transcripts:
            if iteration == 1:
                results.append(
                    EvaluationResult(
                        scenario_id=t.scenario_id,
                        iteration=iteration,
                        scores=[
                            CriterionScore("understanding", 4, "Missed user intent", "I can help with that."),
                            CriterionScore("api_usage", 4, "No booking API use", ""),
                            CriterionScore("confirmation", 4, "No confirmation", ""),
                            CriterionScore("naturalness", 5, "Too generic", "I can help with that."),
                        ],
                        root_cause=RootCause.BOTH,
                        root_cause_explanation="Prompt vague and booking handler missing required validation.",
                        faulty_file="backend/routes/bookings.py",
                        faulty_behaviour="create_booking does not validate fare constraints",
                    )
                )
            else:
                results.append(
                    EvaluationResult(
                        scenario_id=t.scenario_id,
                        iteration=iteration,
                        scores=[
                            CriterionScore("understanding", 9, "Handled request correctly"),
                            CriterionScore("api_usage", 9, "Used correct endpoints"),
                            CriterionScore("confirmation", 9, "Clearly confirmed"),
                            CriterionScore("naturalness", 9, "Natural end-to-end flow"),
                        ],
                        root_cause=RootCause.NONE,
                        root_cause_explanation="No failures.",
                    )
                )
        return results

    def fake_apply_fixes(current_prompt: str, evaluations: list[EvaluationResult]):
        calls.apply_fixes += 1
        return (
            current_prompt + "\n\n# Refinement: enforce explicit confirmation and API checks.",
            [
                Fix(fix_type="prompt", description="Strengthened confirmation/tool-use instructions."),
                Fix(
                    fix_type="code",
                    description="Patched create_booking validation.",
                    target_file="backend/routes/bookings.py",
                    diff="mock diff",
                ),
            ],
        )

    async def fake_push_prompt(new_prompt: str):
        calls.push_prompt += 1

    with patch("refinement_loop.loop.RefinementLoop._simulate_all", new=fake_simulate_all), patch(
        "refinement_loop.loop.evaluate_all", new=fake_evaluate_all
    ), patch("refinement_loop.loop.apply_fixes", new=fake_apply_fixes), patch(
        "refinement_loop.loop.push_prompt", new=fake_push_prompt
    ):
        loop = RefinementLoop(scenario_ids=["book_next_available", "cancel_refund"])
        summary = await loop.run()

    # Assertions
    assert summary.terminated_reason == "passed", f"Expected passed, got {summary.terminated_reason}"
    assert len(summary.iterations) == 2, f"Expected 2 iterations, got {len(summary.iterations)}"
    assert calls.evaluate_all == 2, f"evaluate_all calls={calls.evaluate_all}"
    assert calls.apply_fixes == 1, f"apply_fixes calls={calls.apply_fixes}"
    assert calls.push_prompt == 1, f"push_prompt calls={calls.push_prompt}"

    first_iter_fixes = summary.iterations[0].fixes
    assert any(f.fix_type == "prompt" for f in first_iter_fixes), "Missing prompt fix in iteration 1"
    assert any(f.fix_type == "code" for f in first_iter_fixes), "Missing code fix in iteration 1"

    print("PASS: Loop orchestration (non-ElevenLabs) is autonomous and compliant.")
    print(f"  Iterations: {len(summary.iterations)}")
    print(f"  Termination: {summary.terminated_reason}")
    print(f"  evaluate_all calls: {calls.evaluate_all}")
    print(f"  apply_fixes calls: {calls.apply_fixes}")
    print(f"  push_prompt calls: {calls.push_prompt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
