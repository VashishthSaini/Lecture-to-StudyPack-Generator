import urllib.request
import http.cookiejar
import json
import urllib.error
import socket

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

print("=== Quick Verify All Four Tasks ===")

opener = make_opener()
login(opener, 'testuser', 'password123')
lectures = get_lectures(opener)
lecture_id = lectures['lectures'][0]['id']
print(f"Using Lecture ID {lecture_id}: {lectures['lectures'][0]['title']}")

tasks = [
    ('summary', 'generate a summary'),
    ('notes', 'create study notes'),
    ('questions', 'generate practice questions'),
    ('mcqs', 'create multiple choice questions')
]

for task_type, task_desc in tasks:
    print(f"\n--- {task_type.upper()} ---")
    status, result = generate_study_pack(opener, task_desc, lecture_id)
    print(f"  Status: {status}")
    print(f"  Routed task_type: {result.get('task_type')}")
    print(f"  Chunks used: {result.get('chunks_used')}")
    if status == 200:
        content = result.get('content', '')
        print(f"  Content length: {len(content)} chars")
        # Quick format check
        if task_type == 'mcqs':
            has_mcq = 'A.' in content and 'B.' in content and 'C.' in content and 'D.' in content
            print(f"  MCQ format (A/B/C/D): {'OK' if has_mcq else 'MISSING'}")
        elif task_type == 'summary':
            has_md = '##' in content or '##' in content
            print(f"  Has Markdown headings: {'OK' if has_md else 'CHECK'}")
        elif task_type == 'notes':
            has_md = '#' in content or '##' in content
            print(f"  Has Markdown headings: {'OK' if has_md else 'CHECK'}")
        elif task_type == 'questions':
            has_q = 'Question:' in content or 'Q1' in content
            print(f"  Has Questions: {'OK' if has_q else 'CHECK'}")

print("\n=== All Tasks Verified ===")