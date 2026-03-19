import httpx
import json
import time
from datetime import datetime

print("=" * 80)
print("AUTONOMOUS REFINEMENT LOOP - STARTING AND MONITORING")
print("=" * 80)
print()

start_time = time.time()
start_datetime = datetime.now()

print(f"⏱️  Start time: {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Start the loop
print("🚀 Starting loop...")
try:
    response = httpx.get(
        "http://localhost:8000/loop/start?scenario_ids=book_next_available",
        timeout=10
    )
    
    if response.status_code == 200:
        print(f"✅ Loop started!")
    else:
        print(f"❌ Failed to start: {response.status_code}")
        exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print()
print("=" * 80)
print("MONITORING LOOP PROGRESS")
print("=" * 80)
print()

# Monitor loop
previous_iteration = 0
iteration_start_time = {}

for i in range(600):  # Check for up to 10 minutes
    try:
        response = httpx.get("http://localhost:8000/loop/status", timeout=5)
        data = response.json()
        
        status = data.get("status", "unknown")
        iteration = data.get("iteration", 0)
        
        elapsed = time.time() - start_time
        elapsed_str = f"{int(elapsed//60)}m {int(elapsed%60)}s"
        
        current_time = datetime.now()
        time_str = current_time.strftime("%H:%M:%S")
        
        # Track iteration start times
        if iteration > previous_iteration:
            iteration_start_time[iteration] = elapsed
            previous_iteration = iteration
            print()
            print(f"{'─' * 80}")
            print(f"[{time_str}] ✨ ITERATION {iteration} STARTED")
            print(f"{'─' * 80}")
        
        if status == "running":
            print(f"[{time_str}] 🔄 RUNNING | Iteration {iteration} | Elapsed: {elapsed_str}")
        elif status == "idle":
            elapsed = time.time() - start_time
            elapsed_str = f"{int(elapsed//60)}m {int(elapsed%60)}s"
            print()
            print(f"[{time_str}] ✅ LOOP COMPLETED!")
            print(f"⏱️  Total time: {elapsed_str}")
            print()
            print("=" * 80)
            print("TIMING SUMMARY")
            print("=" * 80)
            
            # Show iteration times
            iterations = sorted(iteration_start_time.keys())
            for idx, it in enumerate(iterations):
                start = iteration_start_time[it]
                if idx + 1 < len(iterations):
                    end = iteration_start_time[iterations[idx + 1]]
                else:
                    end = elapsed
                duration = end - start
                print(f"Iteration {it}: {int(duration//60)}m {int(duration%60)}s")
            
            print()
            print(f"Total: {int(elapsed//60)}m {int(elapsed%60)}s")
            break
        
        time.sleep(2)  # Check every 2 seconds
        
    except Exception as e:
        print(f"[ERROR] {e}")
        time.sleep(2)

print()
print("=" * 80)
print("Check backend logs for detailed results and fixes applied")
print("=" * 80)
