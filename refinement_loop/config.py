"""
Refinement loop configuration.
All thresholds and limits are centralised here so the walkthrough
interviewer can adjust them with a single edit.
"""

import os
from pathlib import Path

# ── Termination ──────────────────────────────────────────────────────────────
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "5"))
PASS_THRESHOLD: float = float(os.getenv("PASS_THRESHOLD", "8.0"))

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
LOGS_DIR = ROOT_DIR / "logs"
BACKEND_DIR = ROOT_DIR / "backend"

SYSTEM_PROMPT_FILE = PROMPTS_DIR / "system_prompt.txt"

# ── API keys ──────────────────────────────────────────────────────────────────
GOOGLE_API_KEY: str = os.environ["GOOGLE_API_KEY"]
ELEVENLABS_API_KEY: str = os.environ["ELEVENLABS_API_KEY"]
ELEVENLABS_AGENT_ID: str = os.environ["ELEVENLABS_AGENT_ID"]

# ── Models ───────────────────────────────────────────────────────────────────────
# Gemini 1.5 Pro for customer sim and fixing (needs reasoning);
# Gemini 1.5 Flash for cheaper evaluations if cost becomes an issue.
CUSTOMER_MODEL: str = os.getenv("CUSTOMER_MODEL", "gemini-1.5-pro")
EVALUATOR_MODEL: str = os.getenv("EVALUATOR_MODEL", "gemini-1.5-pro")
FIXER_MODEL: str = os.getenv("FIXER_MODEL", "gemini-1.5-pro")

# ── Simulation ────────────────────────────────────────────────────────────────
MAX_CONVERSATION_TURNS: int = int(os.getenv("MAX_CONVERSATION_TURNS", "12"))

# ── SSE broadcast (observation UI) ───────────────────────────────────────────
SSE_QUEUE_MAXSIZE: int = 100
