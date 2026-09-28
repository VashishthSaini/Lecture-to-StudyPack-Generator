import urllib.request
import http.cookiejar
import json
import urllib.error
import socket
import sqlite3

socket.setdefaulttimeout(400)

def make_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def login(opener, username, password):
    data = json.dumps({'username': username, 'password': password}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:5000/api/login', data=data, headers={'Content-Type': 'application/json'})
    with opener.open(req) as response:
        return json.loads(response.read().decode())

def get_lectures(opener):
    req = urllib.request.Request('http://127.0.0.1:5000/api/lectures')
    with opener.open(req) as response:
        return json.loads(response.read().decode())

def generate_study_pack(opener, task, lecture_id, provider=None):
    data = json.dumps({'task': task, 'lecture_id': lecture_id, 'provider': provider}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:5000/api/study-pack/generate', data=data, headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with opener.open(req) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def check_study_pack(lecture_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, lecture_id, mcqs, questions, summary, notes, created_at FROM study_packs WHERE lecture_id = ?', (lecture_id,))
    row = c.fetchone()
    conn.close()
    return row

print("=== Test All Four Tasks ===")

opener = make_opener()

print("\n1. Login as testuser...")
login(opener, 'testuser', 'password123')
print("   [OK] Login successful")

print("\n2. Get available lectures...")
lectures = get_lectures(opener)
print(f"   Found {len(lectures['lectures'])} lectures")
for l in lectures['lectures'][:5]:
    print(f"   - ID {l['id']}: {l['title']}")

# Use the latest lecture
lecture_id = lectures['lectures'][0]['id']
print(f"\n3. Using Lecture ID {lecture_id}: {lectures['lectures'][0]['title']}")

# Test each task type
tasks = [
    ('summary', 'generate a summary'),
    ('notes', 'create study notes'),
    ('questions', 'generate practice questions'),
    ('mcqs', 'create multiple choice questions')
]

for task_type, task_desc in tasks:
    print(f"\n{'='*60}")
    print(f"Testing {task_type.upper()}: '{task_desc}'")
    print(f"{'='*60}")
    
    status, result = generate_study_pack(opener, task_desc, lecture_id)
    print(f"   Status: {status}")
    
    if status == 200:
        print(f"   Task type: {result.get('task_type')}")
        print(f"   Provider: {result.get('provider')}")
        print(f"   Model: {result.get('model')}")
        print(f"   Chunks used: {result.get('chunks_used')}")
        content = result.get('content', '')
        print(f"   Content length: {len(content)} chars")
        print(f"   Content preview (first 500 chars):")
        # Handle unicode for Windows console
        preview = content[:500].encode('ascii', 'replace').decode('ascii')
        print(f"   {preview}...")
        if len(content) > 500:
            print(f"   ... (truncated)")
            last_200 = content[-200:].encode('ascii', 'replace').decode('ascii')
            print(f"   Last 200 chars:")
            print(f"   {last_200}")
        
        # Check study_packs table
        row = check_study_pack(lecture_id)
        if row:
            print(f"   [OK] Study pack saved to DB")
            # Check the specific column
            col_map = {'summary': 4, 'notes': 5, 'questions': 3, 'mcqs': 2}
            if task_type in col_map:
                col_val = row[col_map[task_type]]
                if col_val:
                    print(f"   [OK] {task_type} column populated ({len(col_val)} chars)")
                else:
                    print(f"   [WARN] {task_type} column is NULL/empty")
    else:
        err_msg = str(result).encode('ascii', 'replace').decode('ascii')
        print(f"   [FAIL] Error: {err_msg}")

print("\n=== All Tests Complete ===")