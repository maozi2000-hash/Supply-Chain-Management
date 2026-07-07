import urllib.request, urllib.parse, http.cookiejar, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'), timeout=5)

def count(body, key):
    m = re.search(rf'{re.escape(key)}（(\d+)）', body)
    return m.group(1) if m else None

# Test orders by supplier
r = opener.open('http://localhost:5000/orders/?' + urllib.parse.urlencode({'supplier': '优瑞奇'}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print(f'orders ?supplier=优瑞奇: status={r.status} 已装柜={count(body, "已装柜订单")} 未装柜={count(body, "未装柜订单")}')

# Test orders by order_no
r = opener.open('http://localhost:5000/orders/?' + urllib.parse.urlencode({'order_no': 'LFY'}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print(f'orders ?order_no=LFY: status={r.status} 已装柜={count(body, "已装柜订单")} 未装柜={count(body, "未装柜订单")}')

# Test orders by status
r = opener.open('http://localhost:5000/orders/?' + urllib.parse.urlencode({'status': '下单'}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print(f'orders ?status=下单: status={r.status} 已装柜={count(body, "已装柜订单")} 未装柜={count(body, "未装柜订单")}')

# Test orders by date range
r = opener.open('http://localhost:5000/orders/?' + urllib.parse.urlencode({'created_start': '2024-01-01', 'created_end': '2027-12-31'}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print(f'orders ?date_range: status={r.status} 已装柜={count(body, "已装柜订单")} 未装柜={count(body, "未装柜订单")}')

# Test combined
r = opener.open('http://localhost:5000/orders/?' + urllib.parse.urlencode({'supplier': '优瑞奇', 'status': '下单'}), timeout=15)
body = r.read().decode('utf-8', 'ignore')
print(f'orders ?supplier+status: status={r.status} 已装柜={count(body, "已装柜订单")} 未装柜={count(body, "未装柜订单")}')
m = re.search(r'筛选条件：([\s\S]{0,150}?)</span>', body)
if m: print('  summary:', m.group(1).strip())