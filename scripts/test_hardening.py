import requests

BASE = 'http://127.0.0.1:8000'

# 1. Health
r = requests.get(f'{BASE}/api/health')
assert r.status_code == 200, f'Health failed: {r.status_code}'
print('Health OK:', r.json()['status'])

# 2. Cypher write rejection
r = requests.post(f'{BASE}/api/cypher', json={'query': 'MATCH (n) DETACH DELETE n'})
assert r.status_code == 403, f'Expected 403, got {r.status_code}'
detail = r.json().get('detail')
assert detail == 'Read-only clinical safety database: write operations are disabled.', f'Unexpected detail: {detail}'
print('Cypher write guard OK (403):', detail)

# 3. Agent write rejection
r = requests.post(f'{BASE}/api/agent', json={'message': 'MATCH (n) DETACH DELETE n'})
assert r.status_code == 403, f'Expected 403, got {r.status_code}'
assert r.json().get('detail') == 'Read-only clinical safety database: write operations are disabled.'
print('Agent write guard OK (403):', r.json().get('detail'))

# 4. Agent out-of-scope / random string query
r = requests.post(f'{BASE}/api/agent', json={'message': 'asdfghjkl', 'active_medicines': ['Atorvastatin']})
assert r.status_code == 200, f'Expected 200, got {r.status_code}'
data = r.json()
print('Agent out-of-scope OK (200):', data['answer'][:90], '...')
assert 'suggestions' in data and len(data['suggestions']) == 3
print('Agent suggestions:', data['suggestions'])

# 5. Cypher read-only query
r = requests.post(f'{BASE}/api/cypher', json={'query': 'MATCH (m:Medicine) RETURN count(m) AS c'})
assert r.status_code == 200
print('Cypher read OK:', r.json()['rows'])

# 6. Presets
r = requests.get(f'{BASE}/api/presets')
assert r.status_code == 200 and len(r.json()) == 4
print('Presets count OK: 4')

print('ALL ENDPOINT TESTS PASSED CLEANLY!')
