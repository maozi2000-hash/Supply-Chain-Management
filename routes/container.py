import os
import zipfile
import io
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_file, current_app,
)
from flask_login import login_required
from models import db, Order, BookingRecord, ContainerRecord, ContainerImage
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from PIL import Image as PILImage

container_bp = Blueprint("container", __name__, url_prefix="/container")


def _save_uploaded_images(container_record, files):
    """保存上传图片到 uploads/年月/订单号/ 目录，返回图片记录列表"""
    upload_root = current_app.config["UPLOAD_FOLDER"]
    now = datetime.now()
    month_dir = now.strftime("%Y-%m")
    order_no = container_record.order.order_no if container_record.order else "unknown"

    target_dir = os.path.join(upload_root, month_dir, order_no)
    os.makedirs(target_dir, exist_ok=True)

    saved_images = []

    for f in files:
        if not f or not f.filename:
            continue
        if not _allowed_file(f.filename):
            continue

        timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
        safe_name = f"装柜照_{timestamp}.jpg"
        file_path_abs = os.path.join(target_dir, safe_name)
        rel_path = os.path.join(month_dir, order_no, safe_name)

        # 生成缩略图（最大宽度 800px）并保存
        try:
            img = PILImage.open(f.stream)
            img = img.convert("RGB")
            if img.width > 800:
                ratio = 800 / img.width
                new_h = int(img.height * ratio)
                img = img.resize((800, new_h), PILImage.LANCZOS)
            img.save(file_path_abs, "JPEG", quality=85)
        except Exception:
            # 非图片文件或损坏，跳过
            continue

        image_record = ContainerImage(
            container_record_id=container_record.id,
            file_path=rel_path,
            original_name=f.filename,
        )
        db.session.add(image_record)
        saved_images.append(image_record)

    return saved_images


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {
        "jpg", "jpeg", "png", "gif", "webp", "bmp"
    }


# ============================================================
# 列表
# ============================================================
@container_bp.route("/")
@login_required
def list_container():
    page = request.args.get("page", 1, type=int)
    pagination = ContainerRecord.query.order_by(
        db.desc(ContainerRecord.id)
    ).paginate(page=page, per_page=15, error_out=False)

    return render_template(
        "container/list.html",
        active_menu="container",
        container_records=pagination.items,
    )


# ============================================================
# 新增
# ============================================================
@container_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_container():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    bookings = BookingRecord.query.order_by(db.desc(BookingRecord.id)).all()
    selected_order_id = request.args.get("order_id", "")

    if request.method == "POST":
        container = _build_container_from_form(request, None)
        if container is None:
            return render_template(
                "container/form.html",
                active_menu="container",
                container=None,
                orders=orders,
                bookings=bookings,
                selected_order_id=selected_order_id,
            )

        db.session.add(container)
        db.session.flush()  # 获取 container.id

        uploaded_files = request.files.getlist("images")
        _save_uploaded_images(container, uploaded_files)

        # 同步订单状态
        order = db.session.get(Order, container.order_id)
        if order and order.status not in ("装柜完成", "已取消"):
            order.status = "装柜完成"

        db.session.commit()
        flash("装柜记录创建成功", "success")
        return redirect(url_for("container.container_detail", id=container.id))

    return render_template(
        "container/form.html",
        active_menu="container",
        container=None,
        orders=orders,
        bookings=bookings,
        selected_order_id=selected_order_id,
    )


# ============================================================
# 详情
# ============================================================
@container_bp.route("/<int:id>")
@login_required
def container_detail(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    images = sorted(container.images, key=lambda x: x.id, reverse=True)
    return render_template(
        "container/detail.html",
        active_menu="container",
        container=container,
        images=images,
    )


# ============================================================
# 编辑
# ============================================================
@container_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_container(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    orders = Order.query.order_by(Order.created_at.desc()).all()
    bookings = BookingRecord.query.order_by(db.desc(BookingRecord.id)).all()

    if request.method == "POST":
        updated = _build_container_from_form(request, container)
        if updated is None:
            return render_template(
                "container/form.html",
                active_menu="container",
                container=container,
                orders=orders,
                bookings=bookings,
                selected_order_id=str(container.order_id),
            )

        # 追加新图片
        uploaded_files = request.files.getlist("images")
        _save_uploaded_images(container, uploaded_files)

        db.session.commit()
        flash("装柜记录更新成功", "success")
        return redirect(url_for("container.container_detail", id=container.id))

    return render_template(
        "container/form.html",
        active_menu="container",
        container=container,
        orders=orders,
        bookings=bookings,
        selected_order_id=str(container.order_id),
    )


# ============================================================
# 删除
# ============================================================
@container_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_container(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    # 删除关联的图片文件
    for img in container.images:
        file_abs = os.path.join(current_app.config["UPLOAD_FOLDER"], img.file_path)
        if os.path.exists(file_abs):
            try:
                os.remove(file_abs)
            except OSError:
                pass

    db.session.delete(container)
    db.session.commit()
    flash("装柜记录已删除", "success")
    return redirect(url_for("container.list_container"))


# ============================================================
# 导出 ZIP（Excel + 图片）
# ============================================================
@container_bp.route("/<int:id>/export")
@login_required
def export_container(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    order = container.order
    images = container.images

    # 创建内存中的 ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:

        # --- Excel 1：订单信息 ---
        wb = Workbook()
        ws = wb.active
        ws.title = "订单信息"

        header_font = Font(bold=True, size=12)
        header_fill = PatternFill(start_color="1A73E8", end_color="1A73E8", fill_type="solid")
        header_font_white = Font(bold=True, size=12, color="FFFFFF")

        ws.append(["订单信息"])
        ws.merge_cells("A1:B1")
        ws["A1"].font = header_font

        order_data = [
            ("订单号", order.order_no if order else "—"),
            ("客户名称", order.customer_name if order else "—"),
            ("品名", order.product_name if order else "—"),
            ("数量", order.quantity if order else "—"),
            ("状态", order.status if order else "—"),
            ("备注", order.remarks if order else ""),
        ]
        for i, (k, v) in enumerate(order_data, start=2):
            ws.cell(row=i, column=1, value=k).font = Font(bold=True)
            ws.cell(row=i, column=2, value=str(v) if v else "")

        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 30

        wb.save(zf, "订单信息_" + (order.order_no if order else "N/A") + ".xlsx")

        # --- Excel 2：装柜明细 ---
        wb2 = Workbook()
        ws2 = wb2.active
        ws2.title = "装柜明细"

        headers = ["柜号", "装柜日期", "件数", "毛重(KG)", "体积(CBM)", "备注"]
        for col, h in enumerate(headers, 1):
            cell = ws2.cell(row=1, column=col, value=h)
            cell.font = header_font_white
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        row_data = [
            container.container_no or "",
            container.loading_date.strftime("%Y-%m-%d") if container.loading_date else "",
            container.cargo_count or 0,
            container.weight or 0,
            container.volume or 0,
            container.remarks or "",
        ]
        for col, val in enumerate(row_data, 1):
            ws2.cell(row=2, column=col, value=val)

        for col_letter in ["A", "B", "C", "D", "E", "F"]:
            ws2.column_dimensions[col_letter].width = 18

        wb2.save(zf, "装柜数据_" + (order.order_no if order else "N/A") + ".xlsx")

        # --- 图片 ---
        for img in images:
            file_abs = os.path.join(current_app.config["UPLOAD_FOLDER"], img.file_path)
            if os.path.exists(file_abs):
                arcname = f"图片/{img.original_name}"
                zf.write(file_abs, arcname)

    zip_buffer.seek(0)
    filename = f"{(order.order_no if order else 'container')}_{container.loading_date.strftime('%Y-%m-%d') if container.loading_date else ''}_导出.zip"

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=filename,
    )


# ============================================================
# 辅助：从表单构建 ContainerRecord
# ============================================================
def _build_container_from_form(req, existing):
    order_id = req.form.get("order_id", type=int)
    booking_id = req.form.get("booking_id", type=int) or None
    container_no = req.form.get("container_no", "").strip()
    loading_date = req.form.get("loading_date", "")
    cargo_count = req.form.get("cargo_count", 0, type=int)
    weight = req.form.get("weight", 0, type=float)
    volume = req.form.get("volume", 0, type=float)
    remarks = req.form.get("remarks", "").strip()

    if not order_id or not container_no:
        flash("请选择订单并填写柜号", "error")
        return None

    if existing:
        existing.order_id = order_id
        existing.booking_id = booking_id
        existing.container_no = container_no
        existing.loading_date = (
            datetime.strptime(loading_date, "%Y-%m-%d").date() if loading_date else None
        )
        existing.cargo_count = cargo_count
        existing.weight = weight
        existing.volume = volume
        existing.remarks = remarks
        return existing
    else:
        return ContainerRecord(
            order_id=order_id,
            booking_id=booking_id,
            container_no=container_no,
            loading_date=(
                datetime.strptime(loading_date, "%Y-%m-%d").date() if loading_date else None
            ),
            cargo_count=cargo_count,
            weight=weight,
            volume=volume,
            remarks=remarks,
        )
