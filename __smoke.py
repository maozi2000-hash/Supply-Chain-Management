import urllib.request
import urllib.parse
import http.cookiejar

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
req = urllib.request.Request('http://localhost:5000/login', data=data, method='POST')
try:
    r = opener.open(req)
    print('login:', r.status, r.url)
except urllib.error.HTTPError as e:
    print('login HTTPError:', e.code, e.url)
    body = e.read().decode('utf-8', 'ignore')
    print(body[:200])

# List
r = opener.open('http://localhost:5000/container/')
body = r.read().decode('utf-8', 'ignore')
print('list:', r.status, 'len:', len(body))
needles = ['name="sku"', 'name="container_no"', 'name="order_no"', 'name="supplier"', 'name="bl_no"', 'name="custom_name"', 'name="loading_start"', 'name="loading_end"']
for n in needles:
    print(f'  {n!r:30s}:', n in body)

# Search sku
r = opener.open('http://localhost:5000/container/?sku=FGY10001BB')
body = r.read().decode('utf-8', 'ignore')
print('\nsearch sku=:', r.status, 'len:', len(body))
for n in ['筛选条件：', '命中', 'list.html', 'container_no']:
    print(f'  {n!r:30s}:', n in body)

# Search container_no
r = opener.open('http://localhost:5000/container/?container_no=NOPE')
body = r.read().decode('utf-8', 'ignore')
print('\nsearch container_no=NOPE:', r.status, 'len:', len(body))
for n in ['筛选条件：', '没有柜号同时匹配当前筛选条件']:
    print(f'  {n!r:40s}:', n in body)
print('has None or 命中:', '命中' in body, '| no-match msg:', '同时匹配' in body)