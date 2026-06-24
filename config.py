<<<<<<< HEAD
﻿import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Flask 基础配置
SECRET_KEY = os.environ.get("SECRET_KEY", "supplier-mgmt-secret-key-change-me")
DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

# 数据库
DATA_DIR = os.path.join(BASE_DIR, "data")
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(DATA_DIR, "database.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# 文件存储
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EXPORT_FOLDER = os.path.join(BASE_DIR, "exports")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# 分页
ITEMS_PER_PAGE = 15

# 管理员密码（批量删除等敏感操作）
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
=======
import os
from dotenv import load_dotenv

load_dotenv()  # 加载 .env 文件（如果存在）

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Flask 基础配置
SECRET_KEY = os.environ.get("SECRET_KEY", "supplier-mgmt-secret-key-change-me")
DEBUG = os.environ.get("FLASK_DEBUG", "true").lower() == "true"

# 数据库
DATA_DIR = os.path.join(BASE_DIR, "data")

# 数据库连接策略：优先使用 Turso 云数据库，否则回退到本地 SQLite
_turso_url = os.environ.get("TURSO_DATABASE_URL")
_turso_token = os.environ.get("TURSO_AUTH_TOKEN")

if _turso_url:
    # ---- Turso 云数据库模式 ----
    def _create_turso_connection():
        """通过 libsql 客户端 + 适配器创建 Turso 连接"""
        import libsql
        from libsql_adapter import LibSQLAdapter

        raw = libsql.connect(
            database=_turso_url,
            auth_token=_turso_token,
        )
        return LibSQLAdapter(raw)

    SQLALCHEMY_DATABASE_URI = "sqlite://"  # 占位，实际连接由 creator 提供
    SQLALCHEMY_ENGINE_OPTIONS = {
        "creator": _create_turso_connection,
        # creator 模式默认使用 StaticPool，
        # pool_size / pool_recycle / pool_pre_ping 不兼容
    }
else:
    # ---- 本地 SQLite 模式 ----
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(DATA_DIR, "database.db")
    SQLALCHEMY_ENGINE_OPTIONS = {}

SQLALCHEMY_TRACK_MODIFICATIONS = False

# 文件存储
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
EXPORT_FOLDER = os.path.join(BASE_DIR, "exports")
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB

# 分页
ITEMS_PER_PAGE = 15
>>>>>>> c26341a738934a24e8a8eb6787eb9988aac4ab69
