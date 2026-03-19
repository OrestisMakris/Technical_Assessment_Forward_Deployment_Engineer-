import httpx
import json

print("Testing new /tools/verify endpoint...")
print()

try:
    response = httpx.post("http://localhost:8000/tools/verify", timeout=30)
    
    if response.status_code == 200:
        data = response.json()
        print("=" * 80)
        print("TOOL VERIFICATION RESULTS")
        print("=" * 80)
        print()
        print(f"Passed: {data.get('passed', 0)}")
        print(f"Failed: {data.get('failed', 0)}")
        print()
        print("Tool Status:")
        print("-" * 80)
        
        for tool, status in sorted(data.get("tools", {}).items()):
            if "PASS" in status:
                symbol = "✅"
            elif "ERROR" in status or "FAIL" in status:
                symbol = "❌"
            else:
                symbol = "⊘"
            
            print(f"{symbol} {tool:30} {status}")
        
        print()
        print("=" * 80)
        if data.get("failed", 0) == 0:
            print("✅ ALL TOOLS VERIFIED - Ready for loop execution!")
        else:
            print(f"⚠️  {data.get('failed')} tool(s) need attention")
    else:
        print(f"❌ HTTP Status {response.status_code}")
        print(response.text[:500])
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("Make sure backend is running on localhost:8000")
