import urllib.request
import http.cookiejar

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
req = urllib.request.Request('http://127.0.0.1:5000/')
try:
    with opener.open(req) as response:
        html = response.read().decode()
        print('HTML loaded successfully, length:', len(html))
        checks = [
            ('theme-toggle', 'id="themeToggle"'),
            ('header-left', 'class="header-left"'),
            ('header-right', 'class="header-right"'),
            ('auth-card', 'class="card auth-card"'),
            ('account-card', 'class="card account-card"'),
        ]
        for name, text in checks:
            found = text in html
            print('  {}: {}'.format(name, 'OK' if found else 'MISSING'))
except Exception as e:
    print('Error:', e)