"""
Test Gemini evaluation with a real customer transcript to verify:
1. Gemini receives the transcript properly
2. Gemini returns valid JSON
3. Our JSON recovery handles any truncation
"""

import json
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
EVALUATOR_MODEL = "gemini-2.5-flash"

genai.configure(api_key=GOOGLE_API_KEY)

# Sample transcript from real loop execution
SAMPLE_TRANSCRIPT = """
CUSTOMER: Hi there, I'm calling to inquire about booking a new flight.
AGENT: Hello! How can I help you today?
"""

EVAL_SYSTEM = """\
You are an expert quality evaluator for airline customer service AI agents.
You will receive a conversation transcript and the scenario the customer was trying to achieve.

Score the agent on EXACTLY these four criteria, each from 1 to 10:
  1. understanding   — Did the agent correctly identify and respond to the customer's core request?
  2. api_usage       — Were the correct backend operations performed with correct parameters?
  3. confirmation    — Did the agent clearly confirm the outcome to the customer?
  4. naturalness     — Did the conversation flow naturally? Was the agent helpful and polite?

Then classify the root cause of any failures:
  "prompt" — the agent misunderstood or was poorly instructed
  "code"   — an API call failed or returned wrong data
  "both"   — failures span both layers
  "none"   — no failures (all scores ≥ 8)

Respond with ONLY a JSON object matching this schema (no markdown, no extra text):
{
  "scores": {
    "understanding": {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": "<exact agent quote or empty>"},
    "api_usage":     {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": ""},
    "confirmation":  {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": ""},
    "naturalness":   {"score": <1-10>, "rationale": "<≤40 words>", "failure_quote": ""}
  },
  "root_cause": "prompt|code|both|none",
  "root_cause_explanation": "<≤60 words explaining why>",
  "faulty_file": "<filepath or null>",
  "faulty_behaviour": "<one sentence or null>"
}"""

EVAL_USER = """\
SCENARIO
--------
Name: Book next available flight
Customer goal: Book a flight to Tokyo for tomorrow

TRANSCRIPT
----------
{transcript}
"""

async def test_gemini_evaluation():
    print("=" * 80)
    print("🔍 TESTING GEMINI EVALUATION WITH REAL TRANSCRIPT")
    print("=" * 80)
    
    user_msg = EVAL_USER.format(transcript=SAMPLE_TRANSCRIPT)
    
    print(f"\n📝 System Prompt ({len(EVAL_SYSTEM)} chars):")
    print("-" * 80)
    print(EVAL_SYSTEM[:300] + "...")
    print("-" * 80)
    
    print(f"\n📋 User Message ({len(user_msg)} chars):")
    print("-" * 80)
    print(user_msg)
    print("-" * 80)
    
    print(f"\n🚀 Calling Gemini {EVALUATOR_MODEL}...")
    
    try:
        model = genai.GenerativeModel(
            model_name=EVALUATOR_MODEL,
            system_instruction=EVAL_SYSTEM,
        )
        
        resp = model.generate_content(
            user_msg,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=2048,  # Our fix
            ),
        )
        
        raw = resp.text.strip()
        print(f"\n✅ Gemini responded ({len(raw)} chars)")
        
        # Check if response looks like JSON
        if raw.startswith('{'):
            print("✅ Response starts with JSON object")
        else:
            print(f"⚠️ Response doesn't start with '{{': {raw[:50]}")
        
        # Try to parse
        print(f"\n📊 Attempting to parse JSON...")
        try:
            data = json.loads(raw)
            print(f"✅ Valid JSON! Keys: {list(data.keys())}")
            
            # Print scores
            if "scores" in data:
                print(f"\n   Scores:")
                for criterion, details in data["scores"].items():
                    score = details.get("score", "?")
                    print(f"     - {criterion}: {score}/10")
            
            if "root_cause" in data:
                print(f"\n   Root Cause: {data['root_cause']}")
            
            return True
        
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"\n   Raw response (first 300 chars):")
            print(f"   {raw[:300]}")
            
            # Try recovery
            print(f"\n🔧 Attempting JSON recovery...")
            if raw.count('{') > raw.count('}'):
                open_braces = raw.count('{') - raw.count('}')
                raw_fixed = raw + '}' * open_braces
                try:
                    data = json.loads(raw_fixed)
                    print(f"✅ Recovery successful! Parsed after adding {open_braces} closing braces")
                    return True
                except json.JSONDecodeError as e2:
                    print(f"❌ Recovery failed: {e2}")
                    return False
            else:
                print(f"❌ Cannot recover - not enough opening braces")
                return False
    
    except Exception as e:
        print(f"❌ Error calling Gemini: {e}")
        return False

async def main():
    success = await test_gemini_evaluation()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if success:
        print("""
✅ GEMINI EVALUATION IS WORKING

The evaluator should now:
1. Receive transcripts with customer turns
2. Return valid JSON with 4 scores
3. Handle any truncation via recovery mechanism
4. Parse successfully

Next step: Run the loop to see if agent calls tools now.
""")
    else:
        print("""
❌ GEMINI EVALUATION HAS ISSUES

Problems detected:
1. Response format not matching expected JSON
2. JSON parsing failing
3. Recovery mechanism not working

Action needed:
- Check if Gemini API is accessible
- Verify GOOGLE_API_KEY is correct
- Check response content and format
""")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
