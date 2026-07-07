import urllib.request, urllib.parse, http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'), timeout=5)

r = opener.open('http://localhost:5000/orders/', timeout=20)
body = r.read().decode('utf-8', 'ignore')
print('=== /orders/ (默认) ===')
print('  status:', r.status)
print('  has 待装柜 badge:', '待装柜' in body)
print('  has 已装柜 badge:', '已装柜' in body)
print('  has row-pending:', 'row-pending' in body)
print('  has chk-ord:', 'chk-ord' in body)
print('  has order_no input:', 'name="order_no"' in body)
print('  has sku input:', 'name="sku"' in body)
print('  has created_start:', 'name="created_start"' in body)

# Test search mode for orders
r = opener.open('http://localhost:5000/orders/?' + urllib.parse.urlencode({'supplier': '优瑞奇'}), timeout=20)
body = r.read().decode('utf-8', 'ignore')
print('\n=== /orders/?supplier=优瑞奇 (筛选) ===')
print('  status:', r.status)
print('  has 筛选条件:', '筛选条件' in body)
print('  has 待装柜 + 已装柜 同时:', '待装柜' in body and '已装柜' in body)
print('  has chk-ord:', 'chk-ord' in body)

# Test search mode for container
r = opener.open('http://localhost:5000/container/?' + urllib.parse.urlencode({'supplier': '优瑞奇'}), timeout=20)
body = r.read().decode('utf-8', 'ignore')
print('\n=== /container/?supplier=优瑞奇 (筛选) ===')
print('  status:', r.status)
print('  has 筛选条件:', '筛选条件' in body)
print('  has 待装柜 + 已装柜:', '待装柜' in body and '已装柜' in body)

# Test search mode for booking
r = opener.open('http://localhost:5000/booking/?' + urllib.parse.urlencode({'order_no': '111'}), timeout=20)
body = r.read().decode('utf-8', 'ignore')
print('\n=== /booking/?order_no=111 (筛选) ===')
print('  status:', r.status)
print('  has 筛选条件:', '筛选条件' in body)
print('  has bkg-checkbox:', 'bkg-checkbox' in body)