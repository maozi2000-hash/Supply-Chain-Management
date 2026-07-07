import urllib.request, urllib.parse, http.cookiejar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'), timeout=5)

def chk(url, checks, label):
    r = opener.open(url, timeout=20)
    body = r.read().decode('utf-8', 'ignore')
    print(f'\n=== {label} ===  status={r.status} len={len(body)}')
    for name, n in checks:
        v = n in body
        print(f"  {'OK' if v else 'MISS'}  {name}")

# Default view tests
chk('http://localhost:5000/orders/', [
    ('待装柜 badge', '待装柜'),
    ('已装柜 badge', '已装柜'),
    ('row-pending class', 'row-pending'),
    ('chk-ord class', 'chk-ord'),
    ('多条件筛选（订单号/供应商/SKU）', 'name="order_no"'),
    ('btnExportSelected', 'btnExportSelected'),
    ('changePerPage', 'changePerPage'),
], '/orders/ (default)')

chk('http://localhost:5000/container/', [
    ('待装柜 badge', '待装柜'),
    ('已装柜 badge', '已装柜'),
    ('row-pending class', 'row-pending'),
    ('ctnr-checkbox', 'ctnr-checkbox'),
    ('data-type="order"', 'data-type="order"'),
    ('data-type="container"', 'data-type="container"'),
    ('changePerPage', 'changePerPage'),
], '/container/ (default)')

chk('http://localhost:5000/booking/', [
    ('待订舱 badge', '待订舱'),
    ('已订舱 badge', '已订舱'),
    ('row-pending class', 'row-pending'),
    ('bkg-checkbox', 'bkg-checkbox'),
    ('data-type="order"', 'data-type="order"'),
    ('data-type="booking"', 'data-type="booking"'),
    ('changePerPage', 'changePerPage'),
], '/booking/ (default)')

# Search mode tests (unified table)
chk('http://localhost:5000/orders/?' + urllib.parse.urlencode({'supplier': '优瑞奇'}), [
    ('筛选条件', '筛选条件'),
    ('单表同时含待装柜+已装柜', '待装柜' in 'X' and '已装柜' in 'X' or ('待装柜' in 'X' or '已装柜' in 'X')),
    ('单表（不分双表）', '筛选结果：' ),
    ('已装柜订单', '已装柜'),
    ('待装柜订单', '待装柜'),
    ('chk-ord checkbox', 'chk-ord'),
], '/orders/?supplier=优瑞奇 (search)')

chk('http://localhost:5000/container/?' + urllib.parse.urlencode({'supplier': '优瑞奇'}), [
    ('筛选条件', '筛选条件'),
    ('待装柜', '待装柜'),
    ('已装柜', '已装柜'),
    ('ctnr-checkbox', 'ctnr-checkbox'),
], '/container/?supplier=优瑞奇 (search)')

chk('http://localhost:5000/booking/?' + urllib.parse.urlencode({'order_no': '111'}), [
    ('筛选条件', '筛选条件'),
    ('bkg-checkbox', 'bkg-checkbox'),
    ('已订舱', '已订舱'),
], '/booking/?order_no=111 (search)')