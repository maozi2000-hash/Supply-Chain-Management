import urllib.request, urllib.parse, http.cookiejar, sys

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
req = urllib.request.Request('http://localhost:5000/login', data=data, method='POST')
r = opener.open(req)
print('login:', r.status, r.url)

# List
r = opener.open('http://localhost:5000/container/')
body = r.read().decode('utf-8', 'ignore')
print('list:', r.status, 'len:', len(body))
needles = ['name="sku"', 'name="container_no"', 'name="order_no"', 'name="supplier"', 'name="bl_no"', 'name="custom_name"', 'name="loading_start"', 'name="loading_end"']
for n in needles:
    print(f'  {n!r:30s}:', n in body)

# Search by sku
r = opener.open('http://localhost:5000/container/?sku=FGY10001BB')
body = r.read().decode('utf-8', 'ignore')
print('\nsearch ?sku=FGY10001BB:', r.status, 'len:', len(body))
for n in ['筛选条件', '命中', '个柜号']:
    print(f'  {n!r:30s}:', n in body)

# Search by container_no (likely 0 results)
r = opener.open('http://localhost:5000/container/?container_no=NOPE')
body = r.read().decode('utf-8', 'ignore')
print('\nsearch ?container_no=NOPE:', r.status, 'len:', len(body))
for n in ['筛选条件', '命中', '没有柜号同时匹配当前筛选条件']:
    print(f'  {n!r:40s}:', n in body)

# Search by supplier
r = opener.open('http://localhost:5000/container/?supplier=某供应商')
body = r.read().decode('utf-8', 'ignore')
print('\nsearch ?supplier=某供应商:', r.status, 'len:', len(body))
for n in ['筛选条件', '命中']:
    print(f'  {n!r:30s}:', n in body)