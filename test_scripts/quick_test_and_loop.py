"""
Quick test: Is the backend webhook working? Then run loop.
"""

import httpx
import json
import subprocess
import time
import sys
import os

print("=" * 80)
print("🔍 QUICK DIAGNOSTIC & LOOP START")
print("=" * 80)

# Test 1: Backend health
print("\n1. Testing backend health...")
try:
    resp = httpx.get("http://localhost:8000/health", timeout=5)
    print(f"   ✅ Backend is responding: {resp.json()}")
    backend_ok = True
except Exception as e:
    print(f"   ❌ Backend not responding: {e}")
    backend_ok = False

# Test 2: Webhook test
print("\n2. Testing webhook...")
try:
    test_payload = {
        "tool_name": "search_flights",
        "parameters": {"destination": "Tokyo"}
    }
    resp = httpx.post("http://localhost:8000/webhook/elevenlabs", json=test_payload, timeout=5)
    result = resp.json()
    print(f"   ✅ Webhook response: {str(result)[:100]}...")
    webhook_ok = (resp.status_code == 200)
except Exception as e:
    print(f"   ❌ Webhook error: {e}")
    webhook_ok = False

# Test 3: Ngrok tunnel
print("\n3. Testing ngrok tunnel...")
try:
    resp = httpx.get("https://semiacidified-pansophistically-charmain.ngrok-free.dev/health", timeout=5)
    print(f"   ✅ Ngrok tunnel is active: {resp.status_code}")
    ngrok_ok = True
except Exception as e:
    print(f"   ⚠️  Ngrok may be down: {e}")
    ngrok_ok = False

# Summary
print("\n" + "=" * 80)
print("STATUS:")
print("=" * 80)
print(f"Backend: {'✅ OK' if backend_ok else '❌ FAIL'}")
print(f"Webhook: {'✅ OK' if webhook_ok else '❌ FAIL'}")
print(f"Ngrok: {'✅ OK' if ngrok_ok else '⚠️  DOWN'}")

if backend_ok and webhook_ok:
    print("\n✅ READY TO RUN LOOP!")
    print("\n🚀 Starting loop in 3 seconds...")
    time.sleep(3)
    
    print("\nStarting: python run_and_monitor_loop.py")
    result = subprocess.run([sys.executable, "run_and_monitor_loop.py"])
    sys.exit(result.returncode)
else:
    print("\n❌ System not ready. Fix issues above first.")
    print("\nTroubleshooting:")
    if not backend_ok:
        print("   - Backend not running. Run: python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
    if not webhook_ok:
        print("   - Webhook endpoint not working. Check backend logs.")
    if not ngrok_ok:
        print("   - Ngrok tunnel down. Run: python start_ngrok.py")
    sys.exit(1)
