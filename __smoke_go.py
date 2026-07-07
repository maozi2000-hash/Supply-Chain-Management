import urllib.request, urllib.parse, http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'), timeout=5)

# Use small per_page to force multiple pages
r = opener.open('http://localhost:5000/container/?' + urllib.parse.urlencode({'per_page': 1}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print('container per_page=1: status', r.status, 'has GO:', 'GO</button>' in body, 'has pageJumpInput:', 'pageJumpInput' in body, 'has 1/2 or 2/2:', '/2 页' in body or '/3 页' in body)

r = opener.open('http://localhost:5000/booking/?' + urllib.parse.urlencode({'per_page': 1}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print('booking per_page=1: status', r.status, 'has GO:', 'GO</button>' in body, 'has pageJumpInput:', 'pageJumpInput' in body)

r = opener.open('http://localhost:5000/orders/?' + urllib.parse.urlencode({'per_page': 1}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print('orders per_page=1: status', r.status, 'has GO:', 'GO</button>' in body, 'has pageJumpInput:', 'pageJumpInput' in body)