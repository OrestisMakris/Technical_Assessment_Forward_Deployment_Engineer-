import httpx
import json
import time

print("=" * 80)
print("AUTONOMOUS REFINEMENT LOOP - PROGRESS MONITOR")
print("=" * 80)
print()

for i in range(60):  # Check for up to 60 iterations (5 minutes)
    try:
        response = httpx.get("http://localhost:8000/loop/status", timeout=5)
        data = response.json()
        
        status = data.get("status")
        iteration = data.get("iteration", 0)
        
        timestamp = time.strftime("%H:%M:%S")
        
        if status == "running":
            print(f"[{timestamp}] 🔄 RUNNING | Iteration {iteration}")
        elif status == "idle":
            print(f"[{timestamp}] ⏸️  IDLE")
            if i > 0:  # Don't exit immediately (loop might still be starting)
                print()
                print("Loop has finished!")
                print("Check backend logs for results")
                break
        else:
            print(f"[{timestamp}] Status: {status}")
        
        time.sleep(5)  # Check every 5 seconds
        
    except Exception as e:
        print(f"Error checking status: {e}")
        time.sleep(5)

print()
print("=" * 80)
print("To see detailed results, check backend logs or query /loop/stream endpoint")
