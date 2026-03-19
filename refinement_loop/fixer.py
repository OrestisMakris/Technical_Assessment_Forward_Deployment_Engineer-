"""
Fixer: applies targeted fixes based on evaluation results.

Two fix types:
  PROMPT — rewrite the system prompt to address identified failures.
  CODE   — generate a patch for a specific Python function and apply it.

Design decisions
----------------
- The fixer receives ALL failing evaluations at once so it can write a
  single coherent prompt revision instead of many conflicting micro-patches.
- Code patches are function-level: the fixer identifies the faulty function
  in the faulty file and rewrites it. We use a simple search-and-replace
  strategy rather than applying a unified diff (more reliable with LLM output).
- Both fix types can be applied in a single iteration.
- After a code patch the affected FastAPI service is sent SIGHUP to reload
  (works with uvicorn --reload). If that fails we do a full restart.
"""

from __future__ import annotations

import ast
import difflib
import importlib.util
import json
import logging
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from refinement_loop.config import BACKEND_DIR, FIXER_MODEL, PROMPTS_DIR, SYSTEM_PROMPT_FILE, GOOGLE_API_KEY
from refinement_loop.models import EvaluationResult, Fix, RootCause

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


# ── Prompt fixing ─────────────────────────────────────────────────────────────

_PROMPT_FIX_SYSTEM = """\
You are a senior prompt engineer improving a voice AI system prompt for an airline customer service agent.

You will receive:
  1. The current system prompt.
  2. A list of evaluation failures from the most recent test run.

Your task: rewrite the system prompt to fix all identified failures WITHOUT
breaking scenarios that are already passing.

Rules:
  - Keep the prompt concise (≤ 800 words). Verbosity degrades agent performance.
  - Fix root causes, not symptoms. If the agent missed a policy detail, add it.
    If the agent was unclear on confirmation, add an explicit instruction.
  - Preserve the overall structure and tone.
  - Output ONLY the new system prompt text — no explanations, no markdown fences.
"""

_PROMPT_FIX_USER = """\
CURRENT SYSTEM PROMPT
---------------------
{current_prompt}

FAILURES TO FIX
---------------
{failures}
"""


def fix_prompt(
    current_prompt: str,
    failing_evals: list[EvaluationResult],
) -> tuple[str, Fix]:
    """
    Rewrite the system prompt to address prompt-layer failures.
    Returns (new_prompt, Fix record).
    """
    failures_text = _format_failures_for_prompt_fix(failing_evals)

    model = genai.GenerativeModel(
        model_name=FIXER_MODEL,
        system_instruction=_PROMPT_FIX_SYSTEM,
    )
    resp = model.generate_content(
        _PROMPT_FIX_USER.format(
            current_prompt=current_prompt,
            failures=failures_text,
        ),
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=2048,
        ),
    )

    new_prompt = resp.text.strip()

    # Compute a human-readable diff for the UI and logs
    diff = _text_diff(current_prompt, new_prompt, label="system_prompt.txt")

    fix = Fix(
        fix_type="prompt",
        description=f"Rewrote system prompt to address {len(failing_evals)} failing scenario(s).",
        diff=diff,
    )
    logger.info("Prompt fix applied: %d lines changed", diff.count("\n"))
    return new_prompt, fix


def _format_failures_for_prompt_fix(evals: list[EvaluationResult]) -> str:
    lines = []
    for e in evals:
        lines.append(f"Scenario: {e.scenario_id}")
        lines.append(f"Root cause explanation: {e.root_cause_explanation}")
        for s in e.scores:
            if s.score < 8:
                lines.append(f"  - Criterion '{s.name}' scored {s.score}/10: {s.rationale}")
                if s.failure_quote:
                    lines.append(f'    Failure quote: "{s.failure_quote}"')
        lines.append("")
    return "\n".join(lines)


# ── Code fixing ───────────────────────────────────────────────────────────────

_CODE_FIX_SYSTEM = """\
You are a senior Python engineer fixing a bug in a FastAPI backend for an airline booking system.

You will receive:
  1. The full source of the faulty file.
  2. A description of the faulty behaviour.
  3. The test failures that were caused by this bug.

Your task: rewrite ONLY the faulty function (or the minimal set of lines) to
fix the behaviour described. Do not refactor unrelated code.

Output a JSON object with exactly two keys:
{
  "function_name": "<name of the function you are rewriting>",
  "new_source": "<complete new source of that function, properly indented>"
}

No markdown fences. No extra commentary. Only the JSON.
"""

_CODE_FIX_USER = """\
FILE: {filepath}

SOURCE:
{source}

FAULTY BEHAVIOUR: {behaviour}

TEST FAILURES CAUSED BY THIS BUG:
{failures}
"""


def fix_code(
    faulty_file: str,
    faulty_behaviour: str,
    failing_evals: list[EvaluationResult],
) -> Optional[Fix]:
    """
    Generate a targeted function-level patch for a code bug and apply it.
    Returns a Fix record, or None if patching fails.
    """
    filepath = BACKEND_DIR / faulty_file.lstrip("/")
    if not filepath.exists():
        # Try relative to project root
        filepath = Path(faulty_file)
    if not filepath.exists():
        logger.error("Code fix: file not found: %s", faulty_file)
        return None

    original_source = filepath.read_text(encoding="utf-8")

    failures_text = _format_failures_for_code_fix(failing_evals)

    model = genai.GenerativeModel(
        model_name=FIXER_MODEL,
        system_instruction=_CODE_FIX_SYSTEM,
    )
    resp = model.generate_content(
        _CODE_FIX_USER.format(
            filepath=faulty_file,
            source=original_source,
            behaviour=faulty_behaviour,
            failures=failures_text,
        ),
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=2048,
        ),
    )

    raw = resp.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        patch_data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Code fix: could not parse LLM output as JSON: %s", exc)
        return None

    function_name: str = patch_data["function_name"]
    new_func_source: str = patch_data["new_source"]

    # Validate the new source parses
    try:
        ast.parse(new_func_source)
    except SyntaxError as exc:
        logger.error("Code fix: generated function has syntax error: %s", exc)
        return None

    patched_source = _replace_function(original_source, function_name, new_func_source)
    if patched_source is None:
        logger.error("Code fix: could not locate function '%s' in %s", function_name, filepath)
        return None

    diff = _text_diff(original_source, patched_source, label=faulty_file)
    filepath.write_text(patched_source, encoding="utf-8")
    logger.info("Code patch applied to %s (function: %s)", filepath, function_name)

    _reload_backend()

    return Fix(
        fix_type="code",
        description=f"Patched `{function_name}` in {faulty_file}: {faulty_behaviour}",
        target_file=str(filepath),
        diff=diff,
    )


def _format_failures_for_code_fix(evals: list[EvaluationResult]) -> str:
    lines = []
    for e in evals:
        lines.append(f"- Scenario '{e.scenario_id}': {e.root_cause_explanation}")
        for s in e.scores:
            if s.score < 8:
                lines.append(f"  '{s.name}' ({s.score}/10): {s.rationale}")
    return "\n".join(lines)


def _replace_function(source: str, func_name: str, new_func_source: str) -> Optional[str]:
    """
    Find `func_name` in `source` and replace its full body with `new_func_source`.
    Uses AST to locate exact line range; falls back to a regex heuristic.
    """
    try:
        tree = ast.parse(source)
        lines = source.splitlines(keepends=True)

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == func_name:
                    start = node.lineno - 1          # 0-indexed
                    # end_lineno is available in Python 3.8+
                    end = node.end_lineno             # 1-indexed inclusive
                    # Detect decorator lines above the def
                    while start > 0 and lines[start - 1].strip().startswith("@"):
                        start -= 1
                    patched = (
                        "".join(lines[:start])
                        + new_func_source.rstrip()
                        + "\n"
                        + "".join(lines[end:])
                    )
                    return patched
    except Exception as exc:
        logger.warning("AST-based function replace failed: %s", exc)

    # Regex fallback (less precise)
    pattern = re.compile(
        rf"((?:@\w+\([^)]*\)\s*\n)*)"  # decorators
        rf"(async\s+)?def\s+{re.escape(func_name)}\s*\(",
        re.MULTILINE,
    )
    match = pattern.search(source)
    if not match:
        return None

    start_pos = match.start()
    # Find the extent of the function by indentation
    rest = source[match.start():]
    func_lines = rest.splitlines(keepends=True)
    # First line of function body
    indent = len(func_lines[0]) - len(func_lines[0].lstrip())
    end_idx = 1
    while end_idx < len(func_lines):
        line = func_lines[end_idx]
        if line.strip() and (len(line) - len(line.lstrip())) <= indent:
            break
        end_idx += 1

    return source[:start_pos] + new_func_source.rstrip() + "\n" + "".join(func_lines[end_idx:])


def _text_diff(a: str, b: str, label: str) -> str:
    return "\n".join(difflib.unified_diff(
        a.splitlines(),
        b.splitlines(),
        fromfile=f"a/{label}",
        tofile=f"b/{label}",
        lineterm="",
    ))


def _reload_backend() -> None:
    """
    Signal the uvicorn process to reload by sending SIGHUP.
    Falls back to no-op if process not found (tests / CI).
    """
    try:
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn"],
            capture_output=True, text=True, timeout=5,
        )
        pids = result.stdout.strip().split()
        for pid in pids:
            os.kill(int(pid), signal.SIGHUP)
            logger.info("Sent SIGHUP to uvicorn PID %s", pid)
    except Exception as exc:
        logger.warning("Could not reload backend: %s", exc)


# ── Orchestration ─────────────────────────────────────────────────────────────

def apply_fixes(
    current_prompt: str,
    evaluations: list[EvaluationResult],
) -> tuple[str, list[Fix]]:
    """
    Decide what to fix based on the evaluations and apply it.
    Returns (new_prompt, list_of_fixes).
    """
    fixes: list[Fix] = []
    new_prompt = current_prompt

    prompt_failures = [
        e for e in evaluations
        if not e.passed and e.root_cause in (RootCause.PROMPT, RootCause.BOTH)
    ]
    code_failures = [
        e for e in evaluations
        if not e.passed and e.root_cause in (RootCause.CODE, RootCause.BOTH)
    ]

    if prompt_failures:
        new_prompt, prompt_fix = fix_prompt(current_prompt, prompt_failures)
        fixes.append(prompt_fix)

    if code_failures:
        # Group by faulty file and fix each file once
        by_file: dict[str, list[EvaluationResult]] = {}
        for e in code_failures:
            key = e.faulty_file or "unknown"
            by_file.setdefault(key, []).append(e)

        for faulty_file, file_evals in by_file.items():
            if faulty_file == "unknown":
                continue
            # Use the most-common faulty_behaviour description
            behaviour = file_evals[0].faulty_behaviour or "unknown behaviour"
            code_fix = fix_code(faulty_file, behaviour, file_evals)
            if code_fix:
                fixes.append(code_fix)

    return new_prompt, fixes
