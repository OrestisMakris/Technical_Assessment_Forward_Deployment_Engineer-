from __future__ import annotations

import datetime
from pathlib import Path

from refinement_loop.evaluator import evaluate
from refinement_loop.models import ConversationTurn, Transcript
from refinement_loop.scenarios import SCENARIOS
from refinement_loop.simulator import generate_customer_script


def main() -> None:
    scenario = SCENARIOS[0]  # book_next_available

    # 1) Customer simulation via Gemini
    customer_turns = generate_customer_script(scenario)

    # 2) Gemini evaluation on a small synthetic transcript
    transcript = Transcript(
        scenario_id=scenario.id,
        turns=[
            ConversationTurn(role="customer", content="I need the next available flight to Tokyo in economy."),
            ConversationTurn(role="agent", content="Hello there. you today"),
        ],
    )
    result = evaluate(transcript, iteration=1)

    # 3) Save both outputs to TXT
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = logs_dir / f"gemini_customer_simulation_{ts}.txt"

    lines: list[str] = []
    lines.append("GEMINI + CUSTOMER SIMULATION OUTPUT")
    lines.append("=" * 80)
    lines.append("")
    lines.append("SCENARIO")
    lines.append("-" * 80)
    lines.append(f"id: {scenario.id}")
    lines.append(f"name: {scenario.name}")
    lines.append(f"goal: {scenario.customer_goal}")
    lines.append("")
    lines.append("CUSTOMER SIMULATION (Gemini-generated utterances)")
    lines.append("-" * 80)
    for i, turn in enumerate(customer_turns, 1):
        lines.append(f"{i}. {turn}")

    lines.append("")
    lines.append("GEMINI EVALUATION")
    lines.append("-" * 80)
    lines.append(f"scenario_id: {result.scenario_id}")
    lines.append(f"overall_score: {result.overall_score}")
    lines.append(f"passed: {result.passed}")
    lines.append(f"root_cause: {result.root_cause.value}")
    lines.append(f"root_cause_explanation: {result.root_cause_explanation}")
    lines.append("")
    lines.append("Criteria:")
    for score in result.scores:
        lines.append(f"- {score.name}: {score.score}")
        lines.append(f"  rationale: {score.rationale}")
        lines.append(f"  failure_quote: {score.failure_quote}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Saved output to: {out_path}")


if __name__ == "__main__":
    main()
