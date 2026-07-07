import urllib.request, urllib.parse, http.cookiejar, sqlite3, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'), timeout=5)

def count(body, key):
    # match "key（NUM）"
    m = re.search(rf'{re.escape(key)}（(\d+)）', body)
    return m.group(1) if m else None

# Test 1: supplier search
r = opener.open('http://localhost:5000/container/?' + urllib.parse.urlencode({'supplier': '优瑞奇'}), timeout=10)
body = r.read().decode('utf-8', 'ignore')
print(f'?supplier=优瑞奇: status={r.status} 已装柜={count(body, "已装柜")} 待装柜={count(body, "待装柜订单")}')

# Test 2: SKU search (pending via order_items)
conn = sqlite3.connect(r'C:\Users\actpie\Desktop\Github -线下\Supply-Chain-Management\data\database.db')
cur = conn.cursor()
cur.execute('SELECT oi.sku FROM order_items oi JOIN orders o ON oi.order_id=o.id WHERE o.id NOT IN (SELECT DISTINCT order_id FROM container_records WHERE order_id IS NOT NULL) AND o.status NOT IN ("已取消", "装柜完成") LIMIT 1')
v = cur.fetchone()
if v:
    sku = v[0]
    r = opener.open('http://localhost:5000/container/?' + urllib.parse.urlencode({'sku': sku}), timeout=10)
    body = r.read().decode('utf-8', 'ignore')
    print(f'?sku={sku!r}: status={r.status} 已装柜={count(body, "已装柜")} 待装柜={count(body, "待装柜订单")}')

# Test 3: container_no should NOT show pending (since pending has no container)
r = opener.open('http://localhost:5000/container/?' + urllib.parse.urlencode({'container_no': 'CAAU5884921'}), timeout=10)
body = r.read().decode('utf-8', 'ignore')
print(f'?container_no=CAAU5884921: status={r.status} 已装柜={count(body, "已装柜")} 待装柜={count(body, "待装柜订单")}')

# Test 4: order_no should show both
r = opener.open('http://localhost:5000/container/?' + urllib.parse.urlencode({'order_no': '鹅鹅鹅'}), timeout=10)
body = r.read().decode('utf-8', 'ignore')
print(f'?order_no=鹅鹅鹅: status={r.status} 已装柜={count(body, "已装柜")} 待装柜={count(body, "待装柜订单")}')

# Test 5: pending order with sku (look for sku in order_items of pending)
cur.execute('SELECT oi.sku, COUNT(*) FROM order_items oi JOIN orders o ON oi.order_id=o.id WHERE o.id NOT IN (SELECT DISTINCT order_id FROM container_records WHERE order_id IS NOT NULL) AND o.status NOT IN ("已取消", "装柜完成") GROUP BY oi.sku ORDER BY COUNT(*) DESC LIMIT 1')
v = cur.fetchone()
if v:
    sku = v[0]
    print(f'\npending-only SKU test: searching sku={sku!r} (used in {v[1]} pending orders)')
    r = opener.open('http://localhost:5000/container/?' + urllib.parse.urlencode({'sku': sku}), timeout=10)
    body = r.read().decode('utf-8', 'ignore')
    print(f'  status={r.status} 已装柜={count(body, "已装柜")} 待装柜={count(body, "待装柜订单")}')