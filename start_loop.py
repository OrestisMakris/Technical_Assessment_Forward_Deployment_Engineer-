import httpx
import json

print("Starting autonomous refinement loop...")
print("=" * 80)

try:
    response = httpx.get(
        "http://localhost:8000/loop/start?scenario_ids=book_next_available",
        timeout=10
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    print()
    print("=" * 80)
    
    if response.status_code == 200:
        print("✅ Loop started successfully!")
        print()
        print("Monitor progress with:")
        print('  httpx.get("http://localhost:8000/loop/status").json()')
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Failed: {e}")
