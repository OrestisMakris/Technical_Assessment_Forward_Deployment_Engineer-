"""
Shared data models for the refinement loop.
Using dataclasses so there is no runtime Pydantic dependency inside the loop;
the API layer uses Pydantic separately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RootCause(str, Enum):
    PROMPT = "prompt"          # agent misunderstood / poorly instructed
    CODE = "code"              # API wrong data, webhook misfired, logic bug
    BOTH = "both"              # failures span both layers
    NONE = "none"              # no failures


@dataclass
class ConversationTurn:
    role: str          # "customer" | "agent"
    content: str


@dataclass
class Transcript:
    scenario_id: str
    turns: list[ConversationTurn] = field(default_factory=list)

    def as_text(self) -> str:
        lines = []
        for t in self.turns:
            label = "CUSTOMER" if t.role == "customer" else "AGENT"
            lines.append(f"{label}: {t.content}")
        return "\n".join(lines)


@dataclass
class CriterionScore:
    name: str
    score: float          # 1–10
    rationale: str
    failure_quote: str = ""   # exact quote from transcript that caused failure


@dataclass
class EvaluationResult:
    scenario_id: str
    iteration: int
    scores: list[CriterionScore]
    root_cause: RootCause
    root_cause_explanation: str
    faulty_file: Optional[str] = None   # e.g. "backend/routes/bookings.py"
    faulty_behaviour: Optional[str] = None  # short description of the bug
    overall_score: float = 0.0

    def __post_init__(self):
        if self.scores:
            self.overall_score = sum(s.score for s in self.scores) / len(self.scores)

    @property
    def passed(self) -> bool:
        from refinement_loop.config import PASS_THRESHOLD
        return all(s.score >= PASS_THRESHOLD for s in self.scores)

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "iteration": self.iteration,
            "overall_score": round(self.overall_score, 2),
            "passed": self.passed,
            "root_cause": self.root_cause.value,
            "root_cause_explanation": self.root_cause_explanation,
            "faulty_file": self.faulty_file,
            "faulty_behaviour": self.faulty_behaviour,
            "scores": [
                {
                    "criterion": s.name,
                    "score": s.score,
                    "rationale": s.rationale,
                    "failure_quote": s.failure_quote,
                }
                for s in self.scores
            ],
        }


@dataclass
class Fix:
    """Represents one applied fix within an iteration."""
    fix_type: str           # "prompt" | "code"
    description: str        # human-readable explanation of what changed
    target_file: Optional[str] = None   # for code fixes
    diff: str = ""          # unified diff or prompt diff


@dataclass
class IterationResult:
    iteration: int
    evaluations: list[EvaluationResult] = field(default_factory=list)
    fixes: list[Fix] = field(default_factory=list)
    prompt_before: str = ""
    prompt_after: str = ""

    @property
    def all_passed(self) -> bool:
        return all(e.passed for e in self.evaluations)

    @property
    def average_score(self) -> float:
        if not self.evaluations:
            return 0.0
        return sum(e.overall_score for e in self.evaluations) / len(self.evaluations)

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "average_score": round(self.average_score, 2),
            "all_passed": self.all_passed,
            "evaluations": [e.to_dict() for e in self.evaluations],
            "fixes": [
                {
                    "type": f.fix_type,
                    "description": f.description,
                    "target_file": f.target_file,
                    "diff": f.diff,
                }
                for f in self.fixes
            ],
        }


@dataclass
class RunSummary:
    """Written to the structured log file at the end of a run."""
    iterations: list[IterationResult] = field(default_factory=list)
    terminated_reason: str = ""   # "passed" | "max_iterations"
    initial_prompt: str = ""
    final_prompt: str = ""

    def to_dict(self) -> dict:
        first = self.iterations[0].average_score if self.iterations else 0.0
        last = self.iterations[-1].average_score if self.iterations else 0.0
        return {
            "terminated_reason": self.terminated_reason,
            "total_iterations": len(self.iterations),
            "score_improvement": round(last - first, 2),
            "initial_average_score": round(first, 2),
            "final_average_score": round(last, 2),
            "initial_prompt": self.initial_prompt,
            "final_prompt": self.final_prompt,
            "iterations": [i.to_dict() for i in self.iterations],
        }

    def write_log(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
