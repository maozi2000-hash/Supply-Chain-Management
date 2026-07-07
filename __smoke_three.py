import urllib.request, urllib.parse, http.cookiejar, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode('utf-8')
opener.open(urllib.request.Request('http://localhost:5000/login', data=data, method='POST'), timeout=8)

def check(url, expected):
    r = opener.open(url, timeout=20)
    body = r.read().decode('utf-8', 'ignore')
    print(f'\n{url}: status={r.status} len={len(body)}')
    for name, n in expected:
        present = n in body
        print(f'  {name}: {present}')
        if not present:
            # Show first 200 chars
            print(f'    search context: ...{body[max(0,body.find(n)-100):body.find(n)+50] if n in body else "[NOT FOUND]"}...')
    return body

# Test container list (default view, has checkboxes for cr rows)
body = check('http://localhost:5000/container/', [
    ('ctnr-checkbox', 'ctnr-checkbox'),
    ('ctnr-select-all', 'ctnr-select-all'),
    ('per_page select', 'changePerPage(this.value)'),
    ('跳页 input', 'pageJumpInput'),
    ('GO 按钮', '>GO</button>'),
    ('containerSelectBar', 'containerSelectBar'),
    ('btnExportSelected', 'btnExportSelected'),
])

# Test booking list
body = check('http://localhost:5000/booking/', [
    ('bkg-checkbox', 'bkg-checkbox'),
    ('bkg-select-all', 'bkg-select-all'),
    ('per_page select', 'changePerPage(this.value)'),
    ('跳页 input', 'pageJumpInput'),
    ('GO 按钮', '>GO</button>'),
    ('bookingSelectBar', 'bookingSelectBar'),
])

# Test orders list
body = check('http://localhost:5000/orders/', [
    ('chk-ord', 'chk-ord'),
    ('chkAll', 'chkAll'),
    ('per_page select', 'changePerPage(this.value)'),
    ('跳页 input', 'pageJumpInput'),
    ('GO 按钮', '>GO</button>'),
    ('ordersSelectBar', 'ordersSelectBar'),
])