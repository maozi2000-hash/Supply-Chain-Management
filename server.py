"""
供应链管理系统 - 纯 Python 内置模块服务器（不依赖 Flask）
使用 http.server + sqlite3 + json 构建

注意：此服务器仅使用本地 SQLite 文件（data/database.db），
      不支持 Turso 云数据库。
      需要 Turso 请使用 Flask 入口：python app.py
"""
import http.server
import json
import sqlite3
import os
import re
import urllib.parse
import hashlib
import datetime
import io
import csv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "database.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

SESSION_STORE = {}

# ============================================================
# 数据库
# ============================================================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            supplier_name TEXT NOT NULL,
            custom_name TEXT,
            status TEXT DEFAULT '下单',
            remarks TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            sku TEXT NOT NULL,
            warehouse TEXT,
            quantity INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS production_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            start_date TEXT,
            expected_end_date TEXT,
            actual_end_date TEXT,
            status TEXT DEFAULT '待生产',
            remarks TEXT
        );
        CREATE TABLE IF NOT EXISTS booking_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            custom_name TEXT,
            vessel_voyage TEXT,
            bl_no TEXT,
            shipping_company TEXT,
            etd TEXT,
            destination TEXT,
            cutoff_time TEXT,
            status TEXT DEFAULT '待订舱',
            remarks TEXT
        );
        CREATE TABLE IF NOT EXISTS container_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            booking_id INTEGER REFERENCES booking_records(id) ON DELETE SET NULL,
            container_no TEXT,
            loading_date TEXT,
            cargo_count INTEGER DEFAULT 0,
            weight REAL DEFAULT 0,
            volume REAL DEFAULT 0,
            remarks TEXT
        );
        CREATE TABLE IF NOT EXISTS customs_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_record_id INTEGER NOT NULL REFERENCES container_records(id) ON DELETE CASCADE,
            sku TEXT NOT NULL,
            quantity INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS actual_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            container_record_id INTEGER NOT NULL REFERENCES container_records(id) ON DELETE CASCADE,
            sku TEXT NOT NULL,
            quantity INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sku_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT,
            length REAL,
            width REAL,
            height REAL,
            gross_weight REAL,
            unit_cost REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    # 默认管理员
    existing = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not existing:
        pw_hash = hashlib.sha256("admin123".encode()).hexdigest()
        conn.execute("INSERT INTO users (username, password_hash, display_name, role) VALUES (?,?,?,?)",
                     ("admin", pw_hash, "系统管理员", "admin"))
    conn.commit()
    conn.close()

init_db()

# ============================================================
# 模板引擎（极简）
# ============================================================
def render_template(name, **ctx):
    """读取静态 HTML 并做简单变量替换"""
    path = os.path.join(BASE_DIR, "templates", name)
    if not os.path.exists(path):
        return f"<h1>Template not found: {name}</h1>"
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    return html  # 交给前端 JS 处理数据渲染

# ============================================================
# 会话管理
# ============================================================
import uuid

def get_session(headers):
    cookie = headers.get("Cookie", "")
    m = re.search(r"session_id=([^;]+)", cookie)
    if m:
        sid = m.group(1)
        if sid in SESSION_STORE:
            return SESSION_STORE[sid]
    return None

def set_session(user):
    sid = str(uuid.uuid4())
    SESSION_STORE[sid] = {"user_id": user["id"], "username": user["username"], "display_name": user["display_name"] or user["username"], "role": user["role"]}
    return sid

# ============================================================
# 路由处理器
# ============================================================
class APIHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 安静模式

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def send_html(self, html, status=200, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def send_redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def parse_body(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else ""
        if self.headers.get("Content-Type", "").startswith("application/json"):
            return json.loads(body)
        return dict(urllib.parse.parse_qsl(body))

    def get_user(self):
        return get_session(self.headers)

    def require_login(self):
        user = self.get_user()
        if not user:
            self.send_redirect("/static/login.html")
            return None
        return user

    # ---- 路由分发 ----
    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        # 静态文件
        if path.startswith("/static/"):
            return self.serve_static(path[8:])

        # API 路由
        if path == "/api/me":
            user = self.get_user()
            if user:
                return self.send_json({"logged_in": True, "username": user["username"], "display_name": user["display_name"]})
            return self.send_json({"logged_in": False})

        if path == "/api/orders":
            return self.api_list_orders(qs)
        if re.match(r"^/api/orders/(\d+)$", path):
            oid = int(re.match(r"^/api/orders/(\d+)$", path).group(1))
            return self.api_get_order(oid)
        if path == "/api/production":
            return self.api_list_production(qs)
        if path == "/api/booking":
            return self.api_list_booking(qs)
        if path == "/api/container":
            return self.api_list_container(qs)
        if re.match(r"^/api/container/(\d+)$", path):
            cid = int(re.match(r"^/api/container/(\d+)$", path).group(1))
            return self.api_get_container(cid)
        if path == "/api/dashboard":
            return self.api_dashboard()
        if path == "/api/sku":
            return self.api_list_sku(qs)
        if path == "/api/sku/all":
            return self.api_sku_all()

        # 默认返回 index.html
        return self.serve_static("app.html")

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        body = self.parse_body()

        if path == "/api/login":
            return self.api_login(body)
        if path == "/api/logout":
            return self.api_logout()
        if path == "/api/orders":
            return self.api_create_order(body)
        if re.match(r"^/api/orders/(\d+)$", path):
            oid = int(re.match(r"^/api/orders/(\d+)$", path).group(1))
            return self.api_update_order(oid, body)
        if re.match(r"^/api/orders/(\d+)/delete$", path):
            oid = int(re.match(r"^/api/orders/(\d+)/delete$", path).group(1))
            return self.api_delete_order(oid)
        if path == "/api/production":
            return self.api_create_production(body)
        if re.match(r"^/api/production/(\d+)$", path):
            pid = int(re.match(r"^/api/production/(\d+)$", path).group(1))
            return self.api_update_production(pid, body)
        if re.match(r"^/api/production/(\d+)/delete$", path):
            pid = int(re.match(r"^/api/production/(\d+)/delete$", path).group(1))
            return self.api_delete_production(pid)
        if path == "/api/booking":
            return self.api_create_booking(body)
        if re.match(r"^/api/booking/(\d+)$", path):
            bid = int(re.match(r"^/api/booking/(\d+)$", path).group(1))
            return self.api_update_booking(bid, body)
        if re.match(r"^/api/booking/(\d+)/delete$", path):
            bid = int(re.match(r"^/api/booking/(\d+)/delete$", path).group(1))
            return self.api_delete_booking(bid)
        if path == "/api/container":
            return self.api_create_container(body)
        if re.match(r"^/api/container/(\d+)$", path):
            cid = int(re.match(r"^/api/container/(\d+)$", path).group(1))
            return self.api_update_container(cid, body)
        if re.match(r"^/api/container/(\d+)/delete$", path):
            cid = int(re.match(r"^/api/container/(\d+)/delete$", path).group(1))
            return self.api_delete_container(cid)
        if path == "/api/sku":
            return self.api_create_sku(body)
        if re.match(r"^/api/sku/(\d+)$", path):
            sid = int(re.match(r"^/api/sku/(\d+)$", path).group(1))
            return self.api_update_sku(sid, body)
        if re.match(r"^/api/sku/(\d+)/delete$", path):
            sid = int(re.match(r"^/api/sku/(\d+)/delete$", path).group(1))
            return self.api_delete_sku(sid)
        if path == "/api/orders/import-items":
            return self.api_import_items(body)

        self.send_json({"error": "Not found"}, 404)

    # ---- 静态文件 ----
    def serve_static(self, rel_path):
        full = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(full):
            self.send_html("<h1>404</h1>", 404)
            return
        ext = os.path.splitext(full)[1].lower()
        mime_map = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".ico": "image/x-icon",
        }
        mime = mime_map.get(ext, "application/octet-stream")
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.end_headers()
        with open(full, "rb") as f:
            self.wfile.write(f.read())

    # ---- 认证 API ----
    def api_login(self, body):
        username = body.get("username", "").strip()
        password = body.get("password", "")
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, pw_hash)).fetchone()
        conn.close()
        if user:
            sid = set_session(dict(user))
            self.send_json({"success": True, "user": {"username": user["username"], "display_name": user["display_name"]}}, extra_headers={"Set-Cookie": f"session_id={sid}; Path=/; HttpOnly"})
        else:
            self.send_json({"success": False, "error": "用户名或密码错误"}, 401)

    def api_logout(self):
        self.send_json({"success": True}, extra_headers={"Set-Cookie": "session_id=; Path=/; Max-Age=0"})

    # ---- 仪表盘 API ----
    def api_dashboard(self):
        conn = get_db()
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        status_rows = conn.execute("SELECT status, COUNT(*) FROM orders GROUP BY status").fetchall()
        recent = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5").fetchall()
        conn.close()
        return self.send_json({
            "total_orders": total,
            "status_counts": {r[0]: r[1] for r in status_rows},
            "recent_orders": [dict(r) for r in recent],
        })

    # ---- 订单 CRUD ----
    def api_list_orders(self, qs):
        conn = get_db()
        keyword = qs.get("keyword", [""])[0]
        status = qs.get("status", [""])[0]
        page = int(qs.get("page", ["1"])[0])
        per_page = 15
        where = []
        params = []
        if keyword:
            where.append("(order_no LIKE ? OR supplier_name LIKE ?)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        if status:
            where.append("status = ?")
            params.append(status)
        wc = "WHERE " + " AND ".join(where) if where else ""
        count = conn.execute(f"SELECT COUNT(*) FROM orders {wc}", params).fetchone()[0]
        offset = (page - 1) * per_page
        rows = conn.execute(f"SELECT * FROM orders {wc} ORDER BY created_at DESC LIMIT ? OFFSET ?", params + [per_page, offset]).fetchall()
        conn.close()
        return self.send_json({"orders": [dict(r) for r in rows], "total": count, "page": page, "pages": max(1, -(-count // per_page))})

    def api_get_order(self, oid):
        conn = get_db()
        order = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if not order:
            conn.close()
            return self.send_json({"error": "订单不存在"}, 404)
        items = conn.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)).fetchall()
        production = conn.execute("SELECT * FROM production_tasks WHERE order_id=? ORDER BY id DESC", (oid,)).fetchall()
        booking = conn.execute("SELECT * FROM booking_records WHERE order_id=? ORDER BY id DESC", (oid,)).fetchall()
        container = conn.execute("SELECT * FROM container_records WHERE order_id=? ORDER BY id DESC", (oid,)).fetchall()
        conn.close()
        return self.send_json({
            "order": dict(order),
            "items": [dict(it) for it in items],
            "total_quantity": sum(it["quantity"] for it in items),
            "production_tasks": [dict(t) for t in production],
            "booking_records": [dict(b) for b in booking],
            "container_records": [dict(c) for c in container],
        })

    def api_create_order(self, body):
        conn = get_db()
        try:
            items_json = body.get("items_json", "[]")
            if isinstance(items_json, str):
                items = json.loads(items_json)
            else:
                items = items_json
            cur = conn.execute("INSERT INTO orders (order_no, supplier_name, custom_name, status, remarks) VALUES (?,?,?,?,?)",
                               (body["order_no"], body["supplier_name"], body.get("custom_name",""), body.get("status","下单"), body.get("remarks","")))
            oid = cur.lastrowid
            for it in items:
                conn.execute("INSERT INTO order_items (order_id, sku, warehouse, quantity) VALUES (?,?,?,?)",
                             (oid, it.get("sku",""), it.get("warehouse",""), it.get("quantity",0)))
            conn.commit()
            conn.close()
            return self.send_json({"success": True, "id": oid})
        except Exception as e:
            conn.close()
            return self.send_json({"error": str(e)}, 400)

    def api_update_order(self, oid, body):
        conn = get_db()
        conn.execute("UPDATE orders SET order_no=?, supplier_name=?, custom_name=?, status=?, remarks=?, updated_at=datetime('now') WHERE id=?",
                     (body["order_no"], body["supplier_name"], body.get("custom_name",""), body.get("status","下单"), body.get("remarks",""), oid))
        items_json = body.get("items_json", "[]")
        if isinstance(items_json, str):
            items = json.loads(items_json)
        else:
            items = items_json
        conn.execute("DELETE FROM order_items WHERE order_id=?", (oid,))
        for it in items:
            conn.execute("INSERT INTO order_items (order_id, sku, warehouse, quantity) VALUES (?,?,?,?)",
                         (oid, it.get("sku",""), it.get("warehouse",""), it.get("quantity",0)))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    def api_delete_order(self, oid):
        conn = get_db()
        conn.execute("DELETE FROM orders WHERE id=?", (oid,))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    # ---- 生产 API ----
    def api_list_production(self, qs):
        conn = get_db()
        status = qs.get("status", [""])[0]
        where = ""
        params = []
        if status:
            where = "WHERE status = ?"
            params.append(status)
        rows = conn.execute(f"SELECT pt.*, o.order_no FROM production_tasks pt LEFT JOIN orders o ON pt.order_id=o.id {where} ORDER BY pt.id DESC", params).fetchall()
        conn.close()
        return self.send_json({"production_tasks": [dict(r) for r in rows]})

    def api_create_production(self, body):
        conn = get_db()
        cur = conn.execute("INSERT INTO production_tasks (order_id, start_date, expected_end_date, actual_end_date, status, remarks) VALUES (?,?,?,?,?,?)",
                         (body["order_id"], body.get("start_date"), body.get("expected_end_date"), body.get("actual_end_date"), body.get("status","待生产"), body.get("remarks","")))
        pid = cur.lastrowid
        status = body.get("status")
        if status in ("生产中", "已完成"):
            conn.execute("UPDATE orders SET status='生产中' WHERE id=? AND status='下单'", (body["order_id"],))
        conn.commit()
        conn.close()
        return self.send_json({"success": True, "id": pid})

    def api_update_production(self, pid, body):
        conn = get_db()
        conn.execute("UPDATE production_tasks SET order_id=?, start_date=?, expected_end_date=?, actual_end_date=?, status=?, remarks=? WHERE id=?",
                     (body["order_id"], body.get("start_date"), body.get("expected_end_date"), body.get("actual_end_date"), body.get("status"), body.get("remarks",""), pid))
        status = body.get("status")
        if status == "已完成":
            conn.execute("UPDATE orders SET status='生产完成' WHERE id=? AND status IN ('下单','生产中')", (body["order_id"],))
        elif status == "生产中":
            conn.execute("UPDATE orders SET status='生产中' WHERE id=? AND status='下单'", (body["order_id"],))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    def api_delete_production(self, pid):
        conn = get_db()
        conn.execute("DELETE FROM production_tasks WHERE id=?", (pid,))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    # ---- 订舱 API ----
    def api_list_booking(self, qs):
        conn = get_db()
        status = qs.get("status", [""])[0]
        where = ""
        params = []
        if status:
            where = "WHERE br.status = ?"
            params.append(status)
        rows = conn.execute(f"SELECT br.*, o.order_no FROM booking_records br LEFT JOIN orders o ON br.order_id=o.id {where} ORDER BY br.id DESC", params).fetchall()
        conn.close()
        return self.send_json({"booking_records": [dict(r) for r in rows]})

    def api_create_booking(self, body):
        conn = get_db()
        cur = conn.execute("INSERT INTO booking_records (order_id, custom_name, vessel_voyage, bl_no, shipping_company, etd, destination, cutoff_time, status, remarks) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (body["order_id"], body.get("custom_name"), body.get("vessel_voyage"), body.get("bl_no"), body.get("shipping_company"), body.get("etd"), body.get("destination"), body.get("cutoff_time"), body.get("status","待订舱"), body.get("remarks","")))
        bid = cur.lastrowid
        status = body.get("status")
        if status in ("已订舱", "已出运"):
            conn.execute("UPDATE orders SET status='已订舱' WHERE id=? AND status IN ('下单','生产中','生产完成','订舱中')", (body["order_id"],))
        else:
            conn.execute("UPDATE orders SET status='订舱中' WHERE id=? AND status IN ('下单','生产中','生产完成')", (body["order_id"],))
        conn.commit()
        conn.close()
        return self.send_json({"success": True, "id": bid})

    def api_update_booking(self, bid, body):
        conn = get_db()
        conn.execute("UPDATE booking_records SET order_id=?, custom_name=?, vessel_voyage=?, bl_no=?, shipping_company=?, etd=?, destination=?, cutoff_time=?, status=?, remarks=? WHERE id=?",
                     (body["order_id"], body.get("custom_name"), body.get("vessel_voyage"), body.get("bl_no"), body.get("shipping_company"), body.get("etd"), body.get("destination"), body.get("cutoff_time"), body.get("status"), body.get("remarks",""), bid))
        status = body.get("status")
        if status == "已出运":
            conn.execute("UPDATE orders SET status='已订舱' WHERE id=? AND status!='装柜完成'", (body["order_id"],))
        elif status == "已订舱":
            conn.execute("UPDATE orders SET status='已订舱' WHERE id=? AND status NOT IN ('已订舱','装柜完成','已出运','已取消')", (body["order_id"],))
        else:
            conn.execute("UPDATE orders SET status='订舱中' WHERE id=? AND status NOT IN ('已订舱','装柜完成','已出运','已取消')", (body["order_id"],))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    def api_delete_booking(self, bid):
        conn = get_db()
        conn.execute("DELETE FROM booking_records WHERE id=?", (bid,))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    # ---- 装柜 API ----
    def api_list_container(self, qs):
        conn = get_db()
        rows = conn.execute("SELECT cr.*, o.order_no FROM container_records cr LEFT JOIN orders o ON cr.order_id=o.id ORDER BY cr.id DESC").fetchall()
        conn.close()
        return self.send_json({"container_records": [dict(r) for r in rows]})

    def api_get_container(self, cid):
        conn = get_db()
        cr = conn.execute("SELECT cr.*, o.order_no, o.supplier_name FROM container_records cr LEFT JOIN orders o ON cr.order_id=o.id WHERE cr.id=?", (cid,)).fetchone()
        if not cr:
            conn.close()
            return self.send_json({"error": "装柜记录不存在"}, 404)
        customs = conn.execute("SELECT * FROM customs_items WHERE container_record_id=?", (cid,)).fetchall()
        actual = conn.execute("SELECT * FROM actual_items WHERE container_record_id=?", (cid,)).fetchall()
        conn.close()
        return self.send_json({"container": dict(cr), "customs_items": [dict(it) for it in customs], "actual_items": [dict(it) for it in actual]})

    def api_create_container(self, body):
        conn = get_db()
        cur = conn.execute("INSERT INTO container_records (order_id, booking_id, container_no, loading_date, cargo_count, weight, volume, remarks) VALUES (?,?,?,?,?,?,?,?)",
                         (body["order_id"], body.get("booking_id") or None, body["container_no"], body.get("loading_date"), body.get("cargo_count",0), body.get("weight",0), body.get("volume",0), body.get("remarks","")))
        cid = cur.lastrowid
        customs_json = body.get("customs_json", "[]")
        actual_json = body.get("actual_json", "[]")
        if isinstance(customs_json, str):
            customs_data = json.loads(customs_json)
        else:
            customs_data = customs_json
        if isinstance(actual_json, str):
            actual_data = json.loads(actual_json)
        else:
            actual_data = actual_json
        for it in customs_data:
            conn.execute("INSERT INTO customs_items (container_record_id, sku, quantity) VALUES (?,?,?)", (cid, it["sku"], it["quantity"]))
        for it in actual_data:
            conn.execute("INSERT INTO actual_items (container_record_id, sku, quantity) VALUES (?,?,?)", (cid, it["sku"], it["quantity"]))
        conn.execute("UPDATE orders SET status='装柜完成' WHERE id=? AND status NOT IN ('装柜完成','已取消')", (body["order_id"],))
        conn.commit()
        conn.close()
        return self.send_json({"success": True, "id": cid})

    def api_update_container(self, cid, body):
        conn = get_db()
        conn.execute("UPDATE container_records SET order_id=?, booking_id=?, container_no=?, loading_date=?, cargo_count=?, weight=?, volume=?, remarks=? WHERE id=?",
                     (body["order_id"], body.get("booking_id") or None, body["container_no"], body.get("loading_date"), body.get("cargo_count",0), body.get("weight",0), body.get("volume",0), body.get("remarks",""), cid))
        conn.execute("DELETE FROM customs_items WHERE container_record_id=?", (cid,))
        conn.execute("DELETE FROM actual_items WHERE container_record_id=?", (cid,))
        customs_json = body.get("customs_json", "[]")
        actual_json = body.get("actual_json", "[]")
        if isinstance(customs_json, str):
            customs_data = json.loads(customs_json)
        else:
            customs_data = customs_json
        if isinstance(actual_json, str):
            actual_data = json.loads(actual_json)
        else:
            actual_data = actual_json
        for it in customs_data:
            conn.execute("INSERT INTO customs_items (container_record_id, sku, quantity) VALUES (?,?,?)", (cid, it["sku"], it["quantity"]))
        for it in actual_data:
            conn.execute("INSERT INTO actual_items (container_record_id, sku, quantity) VALUES (?,?,?)", (cid, it["sku"], it["quantity"]))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    def api_delete_container(self, cid):
        conn = get_db()
        conn.execute("DELETE FROM container_records WHERE id=?", (cid,))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    # ---- SKU API ----
    def api_list_sku(self, qs):
        conn = get_db()
        keyword = qs.get("keyword", [""])[0]
        where = ""
        params = []
        if keyword:
            where = "WHERE sku LIKE ? OR name LIKE ?"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        rows = conn.execute(f"SELECT * FROM sku_products {where} ORDER BY sku", params).fetchall()
        conn.close()
        return self.send_json({"skus": [dict(r) for r in rows]})

    def api_sku_all(self):
        conn = get_db()
        rows = conn.execute("SELECT * FROM sku_products ORDER BY sku").fetchall()
        conn.close()
        return self.send_json([dict(r) for r in rows])

    def api_create_sku(self, body):
        conn = get_db()
        try:
            conn.execute("INSERT INTO sku_products (sku, name, length, width, height, gross_weight, unit_cost) VALUES (?,?,?,?,?,?,?)",
                         (body["sku"], body.get("name"), body.get("length"), body.get("width"), body.get("height"), body.get("gross_weight"), body.get("unit_cost")))
            conn.commit()
            conn.close()
            return self.send_json({"success": True})
        except sqlite3.IntegrityError:
            conn.close()
            return self.send_json({"error": "SKU 已存在"}, 400)

    def api_update_sku(self, sid, body):
        conn = get_db()
        conn.execute("UPDATE sku_products SET sku=?, name=?, length=?, width=?, height=?, gross_weight=?, unit_cost=? WHERE id=?",
                     (body["sku"], body.get("name"), body.get("length"), body.get("width"), body.get("height"), body.get("gross_weight"), body.get("unit_cost"), sid))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    def api_delete_sku(self, sid):
        conn = get_db()
        conn.execute("DELETE FROM sku_products WHERE id=?", (sid,))
        conn.commit()
        conn.close()
        return self.send_json({"success": True})

    def api_import_items(self, body):
        return self.send_json({"error": "Excel import not supported in basic server; use manual entry"}, 400)

if __name__ == "__main__":
    import socketserver
    port = 5000
    print(f"供应链管理系统启动: http://localhost:{port}")
    with socketserver.TCPServer(("", port), APIHandler) as httpd:
        httpd.serve_forever()
