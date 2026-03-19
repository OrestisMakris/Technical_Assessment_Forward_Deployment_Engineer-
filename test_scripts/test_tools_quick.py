import httpx
import json

print('Testing webhook tools...')
print()

tests = [
    {
        'name': 'search_flights',
        'tool': 'search_flights',
        'params': {'destination': 'London', 'date': '2026-03-25'}
    },
    {
        'name': 'get_policy',
        'tool': 'get_policy',
        'params': {'topic': 'baggage-policy'}
    },
    {
        'name': 'get_flight_status',
        'tool': 'get_flight_status',
        'params': {'flight_id': 'LHR001'}
    }
]

passed = 0
failed = 0

for i, test in enumerate(tests, 1):
    name = test['name']
    print(f'Test {i}: {name}...')
    try:
        response = httpx.post(
            'http://localhost:8000/webhook/elevenlabs',
            json={'tool_name': test['tool'], 'parameters': test['params']},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            print(f'  ✅ Status 200, response OK')
            passed += 1
        else:
            print(f'  ❌ Status {response.status_code}')
            failed += 1
    except Exception as e:
        print(f'  ❌ Error: {str(e)[:60]}')
        failed += 1
    print()

print('=' * 50)
print(f'Results: {passed} passed, {failed} failed')
if failed == 0:
    print('✅ SUCCESS - All tools working! Safe to run loop.')
else:
    print(f'⚠️ {failed} tool(s) failed - check backend logs')
