#!/usr/bin/env python
"""
Run the loop with the new agent prompt that generates realistic responses.
"""

import subprocess
import sys

print("=" * 80)
print("🚀 RUNNING REFINED LOOP WITH NEW PROMPT")
print("=" * 80)
print("""
Agent is now instructed to:
✅ Generate realistic flight options when customer asks to book
✅ Provide booking confirmations with reference numbers
✅ Answer policy questions and handle cancellations
✅ Maintain natural, conversational tone

Expected behavior:
  Customer: "I'd like to book a flight"
  Agent: [Generates realistic flight list]
  Customer: "Book flight FL-201"
  Agent: [Confirms booking with BK-reference]
  
Evaluator will score on:
  1. Understanding (did agent get the request?)
  2. API Usage (are generated responses realistic?)
  3. Confirmation (did agent confirm clearly?)
  4. Naturalness (is conversation natural?)

Starting loop...
""")

result = subprocess.run([sys.executable, "run_and_monitor_loop.py"])
sys.exit(result.returncode)
