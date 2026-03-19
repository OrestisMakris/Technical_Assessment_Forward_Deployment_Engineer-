#!/usr/bin/env python3
"""Check which models are available on the Google API key."""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not set in .env")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    print("Fetching available models...\n")
    models = genai.list_models()
    
    available = []
    for model in models:
        model_name = model.name.split("/")[-1]
        if "generateContent" in model.supported_generation_methods:
            available.append(model_name)
            print(f"✅ {model_name}")
    
    print(f"\n{'='*60}")
    print(f"Total models available: {len(available)}")
    if available:
        print(f"\n💡 Try using one of these in your .env:")
        for model in available[:3]:
            print(f"   CUSTOMER_MODEL={model}")
    else:
        print("\n❌ No models found! Check your API key and quota.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
