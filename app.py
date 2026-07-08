import os
import json as _json
from flask import Flask, render_template
from flask_login import LoginManager
from config import SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from config import UPLOAD_FOLDER, EXPORT_FOLDER, DATA_DIR
from models import db, User


def ensure_schema(app):
    """Add lightweight columns for existing local SQLite databases.
    自动修复：缺少的费用列会被自动添加；已存在则跳过（容错）。
    """
    from sqlalchemy import text
    with app.app_context():
        with db.engine.connect() as conn:
            # 订舱表
            try:
                columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(booking_records)").fetchall()]
                if "eta" not in columns:
                    conn.exec_driver_sql("ALTER TABLE booking_records ADD COLUMN eta VARCHAR(100)")
                    conn.commit()
                conn.exec_driver_sql("UPDATE booking_records SET status = '已订舱' WHERE status = '已出运'")
                conn.commit()
            except Exception as e:
                print(f"[ensure_schema] booking_records 跳过: {e}")

            # 装柜记录：补齐 5 项实际费用字段 + 备注
            try:
                cr_columns = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(container_records)").fetchall()]
                for col, ddl in [
                    ("domestic_transport_fee", "FLOAT DEFAULT 0"),
                    ("ocean_freight_fee",       "FLOAT DEFAULT 0"),
                    ("overseas_truck_fee",      "FLOAT DEFAULT 0"),
                    ("shelving_fee",            "FLOAT DEFAULT 0"),
                    ("other_fee",               "FLOAT DEFAULT 0"),
                    ("fee_remark",              "TEXT"),
                ]:
                    if col not in cr_columns:
                        conn.exec_driver_sql(f"ALTER TABLE container_records ADD COLUMN {col} {ddl}")
                        conn.commit()
            except Exception as e:
                print(f"[ensure_schema] container_records 跳过: {e}")


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["EXPORT_FOLDER"] = EXPORT_FOLDER

    db.init_app(app)

    # 自定义 Jinja2 过滤器：安全输出 JSON（用于订单明细初始数据）
    @app.template_filter("to_json_escaped")
    def to_json_escaped(value):
        if value is None:
            return "[]"
        result = []
        for it in value:
            item_dict = {"sku": it.sku, "quantity": it.quantity}
            if hasattr(it, "warehouse") and it.warehouse is not None:
                item_dict["warehouse"] = it.warehouse
            result.append(item_dict)
        return _json.dumps(result, ensure_ascii=False)

    # 确保目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(EXPORT_FOLDER, exist_ok=True)

    # Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # 注册 Blueprint
    from auth import auth_bp, create_default_admin
    app.register_blueprint(auth_bp)

    from routes.orders import orders_bp
    app.register_blueprint(orders_bp)

    from routes.booking import booking_bp
    app.register_blueprint(booking_bp)

    from routes.container import container_bp
    app.register_blueprint(container_bp)
    from routes.sku import sku_bp
    app.register_blueprint(sku_bp)

    from routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    # 首页仪表盘
    @app.route("/")
    @app.route("/index")
    def index():
        from flask_login import current_user
        from models import Order, BookingRecord
        from sqlalchemy import func

        if not current_user.is_authenticated:
            from flask import redirect, url_for
            return redirect(url_for("auth.login"))

        total_orders = Order.query.count()
        rows = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
        status_counts = {status: count for status, count in rows}
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
        recent_bookings = BookingRecord.query.filter(
            BookingRecord.eta.isnot(None),
            BookingRecord.eta != ""
        ).order_by(BookingRecord.id.desc()).limit(6).all()

        return render_template(
            "index.html",
            active_menu="dashboard",
            total_orders=total_orders,
            status_counts=status_counts,
            recent_orders=recent_orders,
            recent_bookings=recent_bookings,
        )

    # 创建数据库表 + 默认管理员
    with app.app_context():
        db.create_all()
        ensure_schema(app)
        create_default_admin(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
