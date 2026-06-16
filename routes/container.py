import os
import zipfile
import io
import json as _json
from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    send_file, jsonify, current_app,
)
from flask_login import login_required
from models import db, Order, BookingRecord, ContainerRecord, ContainerImage, CustomsItem, ActualItem, OrderItem
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from PIL import Image as PILImage

container_bp = Blueprint("container", __name__, url_prefix="/container")


def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in {"jpg", "jpeg", "png", "gif", "webp", "bmp"}


def _extract_zip_images(container_record, zip_file):
    upload_root = current_app.config["UPLOAD_FOLDER"]
    now = datetime.now()
    month_dir = now.strftime("%Y-%m")
    if container_record.order_id:
        order = db.session.get(Order, container_record.order_id)
        order_no_dir = order.order_no if order else "unknown"
    else:
        order_no_dir = "unknown"
    target_dir = os.path.join(upload_root, month_dir, order_no_dir)
    os.makedirs(target_dir, exist_ok=True)

    saved = []
    try:
        with zipfile.ZipFile(zip_file) as zf:
            for name in zf.namelist():
                if name.endswith("/") or name.startswith("__MACOSX"):
                    continue
                if not _allowed_file(name):
                    continue
                data = zf.read(name)
                try:
                    img = PILImage.open(io.BytesIO(data))
                    img = img.convert("RGB")
                    if img.width > 800:
                        ratio = 800 / img.width
                        img = img.resize((800, int(img.height * ratio)), PILImage.LANCZOS)
                except Exception:
                    continue
                timestamp = now.strftime("%Y%m%d_%H%M%S_%f")
                base = os.path.basename(name) or "image.jpg"
                safe_name = f"装柜照_{timestamp}_{base}"
                abs_path = os.path.join(target_dir, safe_name)
                rel_path = os.path.join(month_dir, order_no_dir, safe_name)
                img.save(abs_path, "JPEG", quality=85)
                saved.append(ContainerImage(
                    container_record_id=container_record.id,
                    file_path=rel_path,
                    original_name=base,
                ))
    except zipfile.BadZipFile:
        return saved, "无效的 ZIP 文件"

    for s in saved:
        db.session.add(s)
    return saved, None


def _save_items(container, customs_json, actual_json):
    CustomsItem.query.filter_by(container_record_id=container.id).delete()
    try:
        customs_data = _json.loads(customs_json)
    except (_json.JSONDecodeError, TypeError):
        customs_data = []
    for d in customs_data:
        sku = d.get("sku", "").strip()
        qty = d.get("quantity", 0)
        if sku:
            db.session.add(CustomsItem(container_record_id=container.id, sku=sku, quantity=qty))

    ActualItem.query.filter_by(container_record_id=container.id).delete()
    try:
        actual_data = _json.loads(actual_json)
    except (_json.JSONDecodeError, TypeError):
        actual_data = []
    for d in actual_data:
        sku = d.get("sku", "").strip()
        qty = d.get("quantity", 0)
        if sku:
            db.session.add(ActualItem(container_record_id=container.id, sku=sku, quantity=qty))


# ============================================================
@container_bp.route("/")
@login_required
def list_container():
    page = request.args.get("page", 1, type=int)
    pagination = ContainerRecord.query.order_by(db.desc(ContainerRecord.id)).paginate(
        page=page, per_page=15, error_out=False
    )
    return render_template(
        "container/list.html", active_menu="container",
        container_records=pagination.items,
    )


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
                "container/form.html", active_menu="container", container=None,
                orders=orders, bookings=bookings, selected_order_id=selected_order_id,
                synced_items=None,
            )

        db.session.add(container)
        db.session.flush()

        zip_file = request.files.get("image_zip")
        if zip_file and zip_file.filename:
            saved, err = _extract_zip_images(container, zip_file)
            if err:
                flash(err, "warning")

        customs_json = request.form.get("customs_json", "[]")
        actual_json = request.form.get("actual_json", "[]")
        _save_items(container, customs_json, actual_json)

        order = db.session.get(Order, container.order_id)
        if order and order.status not in ("装柜完成", "已取消"):
            order.status = "装柜完成"

        db.session.commit()
        flash("装柜记录创建成功", "success")
        return redirect(url_for("container.container_detail", id=container.id))

    synced_items = None
    if selected_order_id:
        order = db.session.get(Order, int(selected_order_id))
        if order:
            synced_items = [{"sku": oi.sku, "quantity": oi.quantity} for oi in order.items]

    return render_template(
        "container/form.html", active_menu="container", container=None,
        orders=orders, bookings=bookings, selected_order_id=selected_order_id,
        synced_items=synced_items,
    )


@container_bp.route("/<int:id>")
@login_required
def container_detail(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    images = sorted(container.images, key=lambda x: x.id, reverse=True)
    customs_items = container.customs_items
    actual_items = container.actual_items
    diff_rows = _compute_diff(customs_items, actual_items)

    return render_template(
        "container/detail.html", active_menu="container",
        container=container, images=images,
        customs_items=customs_items, actual_items=actual_items,
        diff_rows=diff_rows,
    )


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
                "container/form.html", active_menu="container", container=container,
                orders=orders, bookings=bookings,
                selected_order_id=str(container.order_id),
                synced_items=None,
            )

        zip_file = request.files.get("image_zip")
        if zip_file and zip_file.filename:
            saved, err = _extract_zip_images(container, zip_file)
            if err:
                flash(err, "warning")

        customs_json = request.form.get("customs_json", "[]")
        actual_json = request.form.get("actual_json", "[]")
        _save_items(container, customs_json, actual_json)

        db.session.commit()
        flash("装柜记录更新成功", "success")
        return redirect(url_for("container.container_detail", id=container.id))

    customs_data = [{"sku": ci.sku, "quantity": ci.quantity} for ci in container.customs_items]
    actual_data = [{"sku": ai.sku, "quantity": ai.quantity} for ai in container.actual_items]
    synced_items = {"customs": customs_data, "actual": actual_data}

    return render_template(
        "container/form.html", active_menu="container", container=container,
        orders=orders, bookings=bookings,
        selected_order_id=str(container.order_id) if container.order_id else "",
        synced_items=synced_items,
    )


@container_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_container(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    for img in container.images:
        img_abs = os.path.join(current_app.config["UPLOAD_FOLDER"], img.file_path)
        if os.path.exists(img_abs):
            try:
                os.remove(img_abs)
            except OSError:
                pass

    db.session.delete(container)
    db.session.commit()
    flash("装柜记录已删除", "success")
    return redirect(url_for("container.list_container"))


@container_bp.route("/<int:id>/export")
@login_required
def export_container(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    order = container.order
    images = container.images
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        hf = Font(bold=True, size=12, color="FFFFFF")
        hfill = PatternFill(start_color="1A73E8", end_color="1A73E8", fill_type="solid")
        ac = Alignment(horizontal="center")
        prefix = order.order_no if order else "N_A"

        def _save_wb(wb, name):
            b = io.BytesIO()
            wb.save(b)
            b.seek(0)
            zf.writestr(name, b.read())

        wb = Workbook()
        ws = wb.active
        ws.title = "订单信息"
        for k, v in [("订单号", order.order_no if order else ""),
                     ("供应商", order.supplier_name if order else ""),
                     ("柜名", order.custom_name if order else ""),
                     ("状态", order.status if order else "")]:
            r = ws.max_row + 1
            ws.cell(row=r, column=1, value=k).font = Font(bold=True)
            ws.cell(row=r, column=2, value=v)
        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 30
        _save_wb(wb, f"订单信息_{prefix}.xlsx")

        wb2 = Workbook()
        ws2 = wb2.active
        ws2.title = "装柜数据"
        for col, h in enumerate(["柜号","装柜日期","件数","毛重","体积","备注"], 1):
            c = ws2.cell(row=1, column=col, value=h)
            c.font = hf; c.fill = hfill; c.alignment = ac
        ws2.cell(row=2, column=1, value=container.container_no or "")
        ws2.cell(row=2, column=2, value=container.loading_date.strftime("%Y-%m-%d") if container.loading_date else "")
        ws2.cell(row=2, column=3, value=container.cargo_count or 0)
        ws2.cell(row=2, column=4, value=container.weight or 0)
        ws2.cell(row=2, column=5, value=container.volume or 0)
        ws2.cell(row=2, column=6, value=container.remarks or "")
        for cl in ["A","B","C","D","E","F"]:
            ws2.column_dimensions[cl].width = 18
        _save_wb(wb2, f"装柜数据_{prefix}.xlsx")

        _write_items_sheet(zf, container.customs_items, "报关明细", hf, hfill, ac, order)
        _write_items_sheet(zf, container.actual_items, "真实装柜明细", hf, hfill, ac, order)

        diff_rows = _compute_diff(container.customs_items, container.actual_items)
        wb5 = Workbook()
        ws5 = wb5.active
        ws5.title = "差异明细"
        for col, h in enumerate(["SKU","报关数量","真实数量","差异说明"], 1):
            c = ws5.cell(row=1, column=col, value=h)
            c.font = hf; c.fill = hfill; c.alignment = ac
        for i, dr in enumerate(diff_rows, start=2):
            ws5.cell(row=i, column=1, value=dr["sku"])
            ws5.cell(row=i, column=2, value=dr["customs_qty"])
            ws5.cell(row=i, column=3, value=dr["actual_qty"])
            ws5.cell(row=i, column=4, value=dr["desc"])
        for cl in ["A","B","C","D"]:
            ws5.column_dimensions[cl].width = 20
        _save_wb(wb5, f"差异明细_{prefix}.xlsx")

        for img in images:
            img_abs = os.path.join(current_app.config["UPLOAD_FOLDER"], img.file_path)
            if os.path.exists(img_abs):
                zf.write(img_abs, f"图片/{img.original_name}")

    zip_buffer.seek(0)
    fn = f"{prefix}_{container.loading_date.strftime('%Y-%m-%d') if container.loading_date else ''}_导出.zip"
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=fn)


@container_bp.route("/<int:id>/export-diff")
@login_required
def export_diff(id):
    container = db.session.get(ContainerRecord, id)
    if not container:
        flash("装柜记录不存在", "error")
        return redirect(url_for("container.list_container"))

    order = container.order
    diff_rows = _compute_diff(container.customs_items, container.actual_items)

    wb = Workbook()
    ws = wb.active
    ws.title = "差异明细"
    hf = Font(bold=True, size=12, color="FFFFFF")
    hfill = PatternFill(start_color="1A73E8", end_color="1A73E8", fill_type="solid")
    for col, h in enumerate(["SKU", "报关数量", "真实数量", "差异说明"], 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = hf; c.fill = hfill; c.alignment = Alignment(horizontal="center")
    for i, dr in enumerate(diff_rows, start=2):
        ws.cell(row=i, column=1, value=dr["sku"])
        ws.cell(row=i, column=2, value=dr["customs_qty"])
        ws.cell(row=i, column=3, value=dr["actual_qty"])
        ws.cell(row=i, column=4, value=dr["desc"])
    for cl in ["A","B","C","D"]:
        ws.column_dimensions[cl].width = 20

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"差异明细_{order.order_no if order else 'N_A'}.xlsx",
    )


@container_bp.route("/order-items/<int:order_id>")
@login_required
def get_order_items(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"items": [], "message": "订单不存在"})
    items = [{"sku": oi.sku, "quantity": oi.quantity} for oi in order.items]
    return jsonify({"items": items})


@container_bp.route("/import-items", methods=["POST"])
@login_required
def import_items():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "请选择文件"}), 400
    try:
        wb = load_workbook(file, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(min_row=2, values_only=True))
    except Exception:
        return jsonify({"error": "无法读取 Excel 文件"}), 400

    items = []
    for row in rows:
        if not row or not any(row):
            continue
        sku = str(row[0]).strip() if row[0] else ""
        qty_raw = row[1] if len(row) > 1 else 0
        try:
            quantity = int(qty_raw) if qty_raw else 0
        except (ValueError, TypeError):
            continue
        if not sku:
            continue
        items.append({"sku": sku, "quantity": quantity})
    return jsonify({"items": items})


@container_bp.route("/template-items")
@login_required
def template_items():
    wb = Workbook()
    ws = wb.active
    ws.title = "模板"
    hf = Font(bold=True, color="FFFFFF")
    hfill = PatternFill(start_color="1A73E8", end_color="1A73E8", fill_type="solid")
    for col, h in enumerate(["SKU", "数量"], 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = hf; c.fill = hfill
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 15
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="模板.xlsx")


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
        existing.loading_date = datetime.strptime(loading_date, "%Y-%m-%d").date() if loading_date else None
        existing.cargo_count = cargo_count
        existing.weight = weight
        existing.volume = volume
        existing.remarks = remarks
        return existing

    return ContainerRecord(
        order_id=order_id, booking_id=booking_id,
        container_no=container_no,
        loading_date=datetime.strptime(loading_date, "%Y-%m-%d").date() if loading_date else None,
        cargo_count=cargo_count, weight=weight, volume=volume, remarks=remarks,
    )


def _write_items_sheet(zf, items, name, hf, hfill, ac, order):
    wb = Workbook()
    ws = wb.active
    ws.title = name
    for col, h in enumerate(["SKU", "数量"], 1):
        c = ws.cell(row=1, column=col, value=h)
        c.font = hf; c.fill = hfill; c.alignment = ac
    for i, it in enumerate(items, start=2):
        ws.cell(row=i, column=1, value=it.sku)
        ws.cell(row=i, column=2, value=it.quantity)
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 15
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    zf.writestr(f"{name}_{order.order_no if order else 'N_A'}.xlsx", buf.read())


def _compute_diff(customs_items, actual_items):
    customs_map = {}
    for ci in customs_items:
        k = ci.sku.strip().upper()
        customs_map[k] = customs_map.get(k, 0) + ci.quantity

    actual_map = {}
    for ai in actual_items:
        k = ai.sku.strip().upper()
        actual_map[k] = actual_map.get(k, 0) + ai.quantity

    all_keys = set(list(customs_map.keys()) + list(actual_map.keys()))
    result = []
    for key in sorted(all_keys):
        cq = customs_map.get(key, 0)
        aq = actual_map.get(key, 0)
        if cq == aq:
            continue
        orig = key
        for ci in customs_items:
            if ci.sku.strip().upper() == key:
                orig = ci.sku; break
        for ai in actual_items:
            if ai.sku.strip().upper() == key:
                orig = ai.sku; break

        if cq == 0:
            desc = f"仅真实，真实多 {aq}"
        elif aq == 0:
            desc = f"仅报关，报关多 {cq}"
        elif cq > aq:
            desc = f"报关多 {cq - aq}"
        else:
            desc = f"真实多 {aq - cq}"

        result.append({"sku": orig, "customs_qty": cq, "actual_qty": aq, "desc": desc})

    return result
