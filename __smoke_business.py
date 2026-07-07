import urllib.request, urllib.parse, http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'), timeout=5)

for url, label in [
    ('http://localhost:5000/orders/', 'orders'),
    ('http://localhost:5000/container/', 'container'),
    ('http://localhost:5000/booking/', 'booking'),
    ('http://localhost:5000/sku/', 'sku'),
]:
    r = opener.open(url, timeout=15)
    body = r.read().decode('utf-8', 'ignore')
    print(f'\n=== /{label}/ status={r.status} len={len(body)} ===')
    for n in [
        'btn btn-secondary',
        'btn btn-outline-secondary',
        'bg-light text-dark border',
        'bg-light text-secondary border',
        'btn-dark',
        'btn-success',
        '#1a73e8',
        '#fff8e6',
    ]:
        cnt = body.count(n)
        flag = ' (should be 0)' if n in ['btn-dark', 'btn-success', '#1a73e8', '#fff8e6'] else ''
        print(f'  {n}: {cnt}{flag}')