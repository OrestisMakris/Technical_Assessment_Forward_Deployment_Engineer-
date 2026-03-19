"""
Monitor webhook calls in real-time to see if ElevenLabs is calling tools.
Run this in parallel with the loop to watch for incoming tool requests.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("webhook_monitor")

# File to monitor for webhook calls
LOG_FILE = Path("logs") / "run_latest.json"

last_checked = 0
tool_calls = defaultdict(int)

def monitor_logs():
    """Check for any log files and look for webhook calls."""
    
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logger.warning("No logs directory found")
        return
    
    # Get latest log file
    log_files = sorted(logs_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not log_files:
        logger.warning("No log files found")
        return
    
    latest_log = log_files[0]
    
    try:
        with open(latest_log) as f:
            content = f.read()
        
        # Parse lines as separate JSON objects (one per line in many log formats)
        lines = content.strip().split('\n')
        
        webhook_count = 0
        tool_sends = 0
        tool_receives = 0
        
        for line in lines:
            if not line.strip():
                continue
            
            try:
                entry = json.loads(line)
            except:
                continue
            
            # Check for webhook-related entries
            if isinstance(entry, dict):
                msg = str(entry).lower()
                
                if "webhook" in msg or "elevenlabs" in msg:
                    webhook_count += 1
                    tool_name = entry.get("tool_name", "unknown")
                    if tool_name != "unknown":
                        tool_calls[tool_name] += 1
                
                if "sending" in msg and "turn" in msg:
                    tool_sends += 1
                
                if "response" in msg and "agent" in msg:
                    tool_receives += 1
        
        # Print summary
        if webhook_count > 0 or tool_sends > 0 or tool_receives > 0:
            print("\n" + "=" * 80)
            print("✅ WEBHOOK ACTIVITY DETECTED")
            print("=" * 80)
            print(f"Webhook calls: {webhook_count}")
            print(f"Customer turns sent: {tool_sends}")
            print(f"Agent responses received: {tool_receives}")
            
            if tool_calls:
                print(f"\nTool calls by type:")
                for tool, count in sorted(tool_calls.items(), key=lambda x: x[1], reverse=True):
                    print(f"  - {tool}: {count}")
            
            return True
        else:
            return False
    
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return False

async def main():
    """Monitor logs continuously for webhook calls."""
    
    logger.info("=" * 80)
    logger.info("🔍 WEBHOOK CALL MONITOR")
    logger.info("=" * 80)
    logger.info("\nStarting monitoring in 3 seconds...")
    logger.info("Watch for webhook calls while loop runs in another terminal.")
    logger.info("\nExpected behavior:")
    logger.info("  1. Customer sends message to agent")
    logger.info("  2. Agent should call search_flights tool")
    logger.info("  3. Webhook receives POST /webhook/elevenlabs")
    logger.info("  4. Backend returns flight list")
    logger.info("  5. Agent continues conversation")
    logger.info("\n" + "=" * 80 + "\n")
    
    await asyncio.sleep(3)
    
    check_count = 0
    no_activity_count = 0
    
    while True:
        check_count += 1
        found_activity = monitor_logs()
        
        if found_activity:
            no_activity_count = 0
            logger.info("✅ Tool calls detected!")
        else:
            no_activity_count += 1
            if no_activity_count % 5 == 0:
                logger.warning(f"❌ No webhook calls detected ({no_activity_count * 5} sec)")
        
        await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nMonitor stopped.")
