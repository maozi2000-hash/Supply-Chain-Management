import urllib.request, urllib.parse, http.cookiejar, sqlite3

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'))

conn = sqlite3.connect(r'C:\Users\actpie\Desktop\Github -线下\Supply-Chain-Management\data\database.db')
cur = conn.cursor()
for tbl, col in [('container_records', 'container_no'), ('orders', 'order_no'), ('orders', 'supplier_name'), ('booking_records', 'bl_no')]:
    cur.execute(f'SELECT DISTINCT {col} FROM {tbl} WHERE {col} IS NOT NULL AND {col} != "" LIMIT 3')
    print(tbl, col, ':', [r[0] for r in cur.fetchall()])
print()

# Test with first available values
for tbl, col, urlkey in [
    ('container_records', 'container_no', 'container_no'),
    ('orders', 'order_no', 'order_no'),
    ('orders', 'supplier_name', 'supplier'),
    ('booking_records', 'bl_no', 'bl_no'),
]:
    cur.execute(f'SELECT `{col}` FROM {tbl} WHERE `{col}` IS NOT NULL AND `{col}` != "" LIMIT 1')
    row = cur.fetchone()
    if not row: continue
    v = row[0]
    q = urllib.parse.urlencode({urlkey: v})
    r = opener.open('http://localhost:5000/container/?' + q)
    body = r.read().decode('utf-8', 'ignore')
    print(f'?{urlkey}={v!r} ->', r.status, 'len', len(body), 'has 命中:', '命中' in body, 'has no-match:', '没有柜号同时匹配' in body)