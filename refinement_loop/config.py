"""
Refinement loop configuration.
All thresholds and limits are centralised here so the walkthrough
interviewer can adjust them with a single edit.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_AGENT_ID: str = os.getenv("ELEVENLABS_AGENT_ID", "")

# Check which APIs are configured
GOOGLE_CONFIGURED = bool(GOOGLE_API_KEY)
ELEVENLABS_CONFIGURED = bool(ELEVENLABS_API_KEY and ELEVENLABS_AGENT_ID)

if not GOOGLE_CONFIGURED:
    print("⚠️  WARNING: GOOGLE_API_KEY not set — loop will run in DEMO MODE (simplified)")
if not ELEVENLABS_CONFIGURED:
    print("⚠️  WARNING: ELEVENLABS credentials not set — loop will run in FALLBACK MODE (no live agent)")

# ── Models ───────────────────────────────────────────────────────────────────────
# Using gemini-1.5-flash (widely available across all API tiers)
# Faster, cheaper, and suitable for customer sim, evaluation, and fixing
CUSTOMER_MODEL: str = os.getenv("CUSTOMER_MODEL", "gemini-1.5-flash")
EVALUATOR_MODEL: str = os.getenv("EVALUATOR_MODEL", "gemini-1.5-flash")
FIXER_MODEL: str = os.getenv("FIXER_MODEL", "gemini-1.5-flash")

# ── Simulation ────────────────────────────────────────────────────────────────
MAX_CONVERSATION_TURNS: int = int(os.getenv("MAX_CONVERSATION_TURNS", "12"))

# ── SSE broadcast (observation UI) ───────────────────────────────────────────
SSE_QUEUE_MAXSIZE: int = 100
