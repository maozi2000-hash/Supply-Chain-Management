"""
系统级数据备份/恢复路由
- /admin/backup : 直接下载 data/database.db
- /admin/restore : 上传 db 文件，先自动备份当前，再替换
"""
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

from flask import (
    Blueprint, send_file, request, jsonify,
    current_app, abort, flash, redirect, url_for,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from config import ADMIN_PASSWORD, DATA_DIR
from models import db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# 备份目录
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def _require_admin():
    """必须是 admin 角色"""
    if not current_user.is_authenticated:
        abort(401)
    if getattr(current_user, "role", "user") != "admin":
        abort(403)


# ============================================================
# 备份：直接下载 data/database.db
# ============================================================
@admin_bp.route("/backup", methods=["GET"])
@login_required
def backup_database():
    _require_admin()

    db_path = os.path.join(DATA_DIR, "database.db")
    if not os.path.exists(db_path):
        return jsonify({"success": False, "error": "数据库文件不存在"}), 404

    # 先把当前 db 同步到磁盘再读取
    db.session.commit()
    db.session.remove()

    # 把文件流式发送给前端
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"supply-chain-backup-{timestamp}.db"
    return send_file(
        db_path,
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=download_name,
    )


# ============================================================
# 恢复：上传 db 文件替换
# ============================================================
@admin_bp.route("/restore", methods=["POST"])
@login_required
def restore_database():
    _require_admin()

    # ---- 二次安全验证 ----
    admin_password = request.form.get("admin_password", "")
    hold_confirmed = request.form.get("hold_confirmed", "").strip().lower()

    if not admin_password:
        return jsonify({"success": False, "error": "请输入管理员密码"}), 400
    if admin_password != ADMIN_PASSWORD:
        return jsonify({"success": False, "error": "管理员密码错误"}), 403
    if hold_confirmed != "yes":
        return jsonify({"success": False, "error": "请长按确认按钮 1.5 秒"}), 400

    # ---- 检查上传文件 ----
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"success": False, "error": "请选择 .db 文件"}), 400

    safe_name = secure_filename(file.filename)
    if not safe_name.lower().endswith(".db"):
        return jsonify({"success": False, "error": "只支持 .db 文件"}), 400

    # ---- 保存到临时文件，验证是合法 SQLite ----
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        # 验证文件是合法的 SQLite
        try:
            conn = sqlite3.connect(tmp_path)
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check")
            result = cur.fetchone()
            conn.close()
            if not result or result[0].lower() != "ok":
                os.unlink(tmp_path)
                return jsonify({
                    "success": False,
                    "error": f"文件 SQLite 完整性检查失败: {result[0] if result else 'unknown'}"
                }), 400
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return jsonify({"success": False, "error": f"文件不是有效的 SQLite 数据库: {e}"}), 400

        # 验证必有的表（至少要有 users 表）
        try:
            conn = sqlite3.connect(tmp_path)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            has_users = cur.fetchone() is not None
            conn.close()
            if not has_users:
                os.unlink(tmp_path)
                return jsonify({
                    "success": False,
                    "error": "数据库结构不匹配：缺少 users 表，请确认是从本系统导出的备份"
                }), 400
        except Exception as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            return jsonify({"success": False, "error": f"数据库表结构校验失败: {e}"}), 400

    except Exception as e:
        return jsonify({"success": False, "error": f"读取上传文件失败: {e}"}), 500

    # ---- 关闭所有 SQLAlchemy 连接，备份当前 db，再替换 ----
    db_path = os.path.join(DATA_DIR, "database.db")
    try:
        # 1. 关闭所有会话
        db.session.commit()
        db.session.remove()
        # 2. 清空连接池，让所有连接关闭
        db.engine.dispose()

        # 3. 备份当前 db（如果存在）
        backup_path = None
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"database-auto-backup-before-restore-{timestamp}.db"
            backup_path = os.path.join(BACKUP_DIR, backup_name)
            shutil.copy2(db_path, backup_path)

        # 4. 替换 db 文件
        shutil.copy2(tmp_path, db_path)
        os.unlink(tmp_path)

        # 5. 再次 dispose 让后续查询重新打开新文件
        db.engine.dispose()

    except Exception as e:
        # 失败时尝试恢复（如果有备份的话）
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return jsonify({"success": False, "error": f"替换数据库失败: {e}"}), 500

    return jsonify({
        "success": True,
        "message": "数据库恢复成功！页面将在 3 秒后刷新。",
        "backup": os.path.basename(backup_path) if backup_path else None,
    })
