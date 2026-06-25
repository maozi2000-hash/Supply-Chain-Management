import os

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
