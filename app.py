import os
import json as _json
from flask import Flask, render_template
from flask_login import LoginManager
from config import SECRET_KEY, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from config import UPLOAD_FOLDER, EXPORT_FOLDER, DATA_DIR
from models import db, User


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

    from routes.production import production_bp
    app.register_blueprint(production_bp)

    from routes.booking import booking_bp
    app.register_blueprint(booking_bp)

    from routes.container import container_bp
    app.register_blueprint(container_bp)

    # 首页仪表盘
    @app.route("/")
    @app.route("/index")
    def index():
        from flask_login import current_user
        from models import Order
        from sqlalchemy import func

        if not current_user.is_authenticated:
            from flask import redirect, url_for
            return redirect(url_for("auth.login"))

        total_orders = Order.query.count()
        rows = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
        status_counts = {status: count for status, count in rows}
        recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

        return render_template(
            "index.html",
            active_menu="dashboard",
            total_orders=total_orders,
            status_counts=status_counts,
            recent_orders=recent_orders,
        )

    # 创建数据库表 + 默认管理员
    with app.app_context():
        db.create_all()
        create_default_admin(app)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
