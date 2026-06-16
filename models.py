from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone

db = SQLAlchemy()

# ============================================================
# 用户表
# ============================================================
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    display_name = db.Column(db.String(50))
    role = db.Column(db.String(10), default="user")  # admin / user
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


# ============================================================
# 订单表
# ============================================================
class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False, index=True)
    supplier_name = db.Column(db.String(100), nullable=False)
    custom_name = db.Column(db.String(200))
    status = db.Column(db.String(20), default="下单")  # 下单/生产中/生产完成/订舱中/已订舱/装柜完成/已取消
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # 关联
    production_tasks = db.relationship(
        "ProductionTask", backref="order", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    booking_records = db.relationship(
        "BookingRecord", backref="order", lazy="dynamic",
        cascade="all, delete-orphan"
    )
    container_records = db.relationship(
        "ContainerRecord", backref="order", lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # 订单明细
    items = db.relationship(
        "OrderItem", backref="order", lazy="select",
        cascade="all, delete-orphan"
    )


# ============================================================
# 生产任务表
# ============================================================
class ProductionTask(db.Model):
    __tablename__ = "production_tasks"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    start_date = db.Column(db.Date)
    expected_end_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)
    status = db.Column(db.String(10), default="待生产")  # 待生产/生产中/已完成
    remarks = db.Column(db.Text)


# ============================================================
# 订舱记录表
# ============================================================
class BookingRecord(db.Model):
    __tablename__ = "booking_records"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    custom_name = db.Column(db.String(100))         # 柜名（客户自定义）
    vessel_voyage = db.Column(db.String(200))       # 航名/航次
    bl_no = db.Column(db.String(100))               # 提单号
    shipping_company = db.Column(db.String(100))     # 船公司
    etd = db.Column(db.Date)                        # 开航日期(ETD)
    destination = db.Column(db.String(100))          # 目地港
    cutoff_time = db.Column(db.String(100))          # 截单时间
    status = db.Column(db.String(10), default="待订舱")  # 待订舱/已订舱/已出运
    remarks = db.Column(db.Text)                     # 备注


# ============================================================
# 装柜记录表
# ============================================================
class ContainerRecord(db.Model):
    __tablename__ = "container_records"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking_records.id", ondelete="SET NULL"), nullable=True)
    container_no = db.Column(db.String(50))
    loading_date = db.Column(db.Date)
    cargo_count = db.Column(db.Integer, default=0)
    weight = db.Column(db.Float, default=0)
    volume = db.Column(db.Float, default=0)
    remarks = db.Column(db.Text)

    # 关联
    booking = db.relationship("BookingRecord", backref="container_records")
    images = db.relationship(
        "ContainerImage", backref="container_record", lazy="select",
        cascade="all, delete-orphan"
    )


# ============================================================
# 装柜图片表
# ============================================================
class ContainerImage(db.Model):
    __tablename__ = "container_images"

    id = db.Column(db.Integer, primary_key=True)
    container_record_id = db.Column(
        db.Integer, db.ForeignKey("container_records.id", ondelete="CASCADE"), nullable=False
    )
    file_path = db.Column(db.String(500))  # 相对路径
    original_name = db.Column(db.String(200))
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# ============================================================
# 订单明细表
# ============================================================
class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    sku = db.Column(db.String(100), nullable=False)
    warehouse = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=0)
