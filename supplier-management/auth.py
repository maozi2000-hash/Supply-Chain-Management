from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

auth_bp = Blueprint("auth", __name__)


def create_default_admin(app):
    """首次启动时自动创建默认管理员"""
    with app.app_context():
        if User.query.filter_by(username="admin").first() is None:
            admin = User(
                username="admin",
                password_hash=generate_password_hash("admin123"),
                display_name="系统管理员",
                role="admin",
            )
            db.session.add(admin)
            db.session.commit()
            app.logger.info("默认管理员账号已创建: admin / admin123")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("登录成功", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash("用户名或密码错误", "error")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("auth.login"))
