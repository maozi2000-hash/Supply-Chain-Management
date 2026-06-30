from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_required
from models import db, Order, BookingRecord
from datetime import datetime

booking_bp = Blueprint("booking", __name__, url_prefix="/booking")


@booking_bp.route("/")
@login_required
def list_booking():
    """统一列表：未填订舰的订单 + 已填订舰的记录"""
    current_status = request.args.get("status", "").strip()
    query = BookingRecord.query
    if current_status and current_status in ("待订舰", "已订舰", "已出运"):
        query = query.filter(BookingRecord.status == current_status)
    pagination = query.order_by(db.desc(BookingRecord.id)).paginate(
        page=request.args.get("page", 1, type=int), per_page=15, error_out=False
    )
    pending_subq = db.session.query(BookingRecord.order_id).distinct()
    pending_orders = Order.query.filter(
        ~Order.id.in_(pending_subq)
    ).order_by(db.desc(Order.created_at)).limit(50).all()
    return render_template(
        "booking/list.html",
        active_menu="booking",
        booking_records=pagination.items,
        pending_orders=pending_orders,
        current_status=current_status,
        pagination=pagination,
    )


@booking_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_booking():
    pending_subq = db.session.query(BookingRecord.order_id).distinct()
    pending_orders = Order.query.filter(
        ~Order.id.in_(pending_subq)
    ).order_by(db.desc(Order.created_at)).all()
    orders = Order.query.order_by(Order.created_at.desc()).all()
    target_order_id = (
        request.args.get("order_id")
        or session.get("last_created_order_id")
        or (str(pending_orders[0].id) if pending_orders else "")
    )
    target_order = db.session.get(Order, int(target_order_id)) if target_order_id else None
    prefill = {
        "custom_name": target_order.custom_name or "" if target_order else "",
        "vessel_voyage": "", "bl_no": "", "shipping_company": "",
        "etd": "", "destination": "", "cutoff_time": "",
        "status": "待订舰", "remarks": "",
    }
    if request.method == "POST":
        order_id = request.form.get("order_id", type=int)
        status = request.form.get("status", "待订舰")
        custom_name = request.form.get("custom_name", "").strip()
        vessel_voyage = request.form.get("vessel_voyage", "").strip()
        bl_no = request.form.get("bl_no", "").strip()
        shipping_company = request.form.get("shipping_company", "").strip()
        etd = request.form.get("etd", "").strip()
        destination = request.form.get("destination", "").strip()
        cutoff_time = request.form.get("cutoff_time", "").strip()
        remarks = request.form.get("remarks", "").strip()
        if not order_id:
            flash("请选择关联订单", "error")
            return render_template("booking/form.html", active_menu="booking", booking=None, orders=orders,
                                   target_order=target_order, pending_orders=pending_orders, prefill=prefill)
        if not vessel_voyage and not shipping_company:
            flash("航名/航次与船公司至少填一项", "error")
            return render_template("booking/form.html", active_menu="booking", booking=None, orders=orders,
                                   target_order=target_order, pending_orders=pending_orders, prefill=prefill)
        br = BookingRecord(
            custom_name=custom_name, vessel_voyage=vessel_voyage, bl_no=bl_no,
            shipping_company=shipping_company,
            etd=datetime.strptime(etd, "%Y-%m-%d").date() if etd else None,
            destination=destination, cutoff_time=cutoff_time,
            order_id=order_id, status=status, remarks=remarks,
        )
        db.session.add(br)
        order = db.session.get(Order, order_id)
        if order and order.status in ("下单", "生产中", "生产完成"):
            if status in ("已订舰", "已出运"):
                order.status = "已订舰"
            else:
                order.status = "订舰中"
        db.session.commit()
        session.pop("last_created_order_id", None)
        flash("订舰记录创建成功", "success")
        return redirect(url_for("booking.list_booking"))
    return render_template("booking/form.html", active_menu="booking", booking=None, orders=orders,
                           target_order=target_order, pending_orders=pending_orders, prefill=prefill)


@booking_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_booking(id):
    booking = db.session.get(BookingRecord, id)
    if not booking:
        flash("订舰记录不存在", "error")
        return redirect(url_for("booking.list_booking"))
    orders = Order.query.order_by(Order.created_at.desc()).all()
    if request.method == "POST":
        booking.custom_name = request.form.get("custom_name", "").strip()
        booking.vessel_voyage = request.form.get("vessel_voyage", "").strip()
        booking.bl_no = request.form.get("bl_no", "").strip()
        booking.shipping_company = request.form.get("shipping_company", "").strip()
        etd = request.form.get("etd", "").strip()
        booking.etd = datetime.strptime(etd, "%Y-%m-%d").date() if etd else None
        booking.destination = request.form.get("destination", "").strip()
        booking.cutoff_time = request.form.get("cutoff_time", "").strip()
        booking.order_id = request.form.get("order_id", type=int)
        booking.status = request.form.get("status", "待订舰")
        booking.remarks = request.form.get("remarks", "").strip()
        order = db.session.get(Order, booking.order_id)
        if order:
            if booking.status == "已出运" and order.status != "装柜完成":
                order.status = "已订舰"
            elif booking.status == "已订舰":
                order.status = "已订舰"
            elif order.status not in ("已订舰", "装柜完成", "已出运", "已取消"):
                order.status = "订舰中"
        db.session.commit()
        flash("订舰记录更新成功", "success")
        return redirect(url_for("booking.list_booking"))
    return render_template("booking/form.html", active_menu="booking", booking=booking, orders=orders,
                           selected_order_id=str(booking.order_id) if booking.order_id else "")


@booking_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_booking(id):
    br = db.session.get(BookingRecord, id)
    if not br:
        flash("订舰记录不存在", "error")
        return redirect(url_for("booking.list_booking"))
    db.session.delete(br)
    db.session.commit()
    flash("订舰记录已删除", "success")
    return redirect(url_for("booking.list_booking"))
