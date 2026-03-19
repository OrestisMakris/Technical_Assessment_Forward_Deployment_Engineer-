"""
Push the updated system prompt to ElevenLabs agent immediately.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add refinement_loop to path
sys.path.insert(0, str(Path(__file__).parent))

from refinement_loop.elevenlabs_client import push_prompt, get_current_prompt
from refinement_loop.config import ELEVENLABS_AGENT_ID

load_dotenv()

async def main():
    print("=" * 80)
    print("🚀 PUSHING UPDATED SYSTEM PROMPT TO ELEVENLABS")
    print("=" * 80)
    
    # Read new prompt
    prompt_file = Path("prompts/system_prompt.txt")
    if not prompt_file.exists():
        print(f"❌ Prompt file not found: {prompt_file}")
        return False
    
    new_prompt = prompt_file.read_text(encoding="utf-8")
    print(f"\n📝 New prompt ({len(new_prompt)} chars):")
    print("-" * 80)
    print(new_prompt[:500] + "...")
    print("-" * 80)
    
    # Push to ElevenLabs
    print(f"\n📤 Pushing to ElevenLabs agent: {ELEVENLABS_AGENT_ID}")
    try:
        await push_prompt(new_prompt)
        print("✅ Prompt pushed successfully!")
    except Exception as e:
        print(f"❌ Error pushing prompt: {e}")
        return False
    
    # Verify
    print(f"\n✓ Verifying...")
    try:
        current = await get_current_prompt()
        if current[:50] in new_prompt[:50]:
            print("✅ Verification successful - new prompt is active")
            return True
        else:
            print("⚠️ Warning: Current prompt doesn't match")
            print(f"   Expected start: {new_prompt[:50]}...")
            print(f"   Got start: {current[:50]}...")
            return False
    except Exception as e:
        print(f"⚠️ Could not verify: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
