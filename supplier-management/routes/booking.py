from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Order, BookingRecord
from datetime import datetime

booking_bp = Blueprint("booking", __name__, url_prefix="/booking")


@booking_bp.route("/")
@login_required
def list_booking():
    current_status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)

    query = BookingRecord.query

    if current_status and current_status in ("待订舱", "已订舱", "已出运"):
        query = query.filter(BookingRecord.status == current_status)

    query = query.order_by(db.desc(BookingRecord.id))
    pagination = query.paginate(page=page, per_page=15, error_out=False)

    return render_template(
        "booking/list.html",
        active_menu="booking",
        booking_records=pagination.items,
        current_status=current_status,
    )


@booking_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_booking():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    selected_order_id = request.args.get("order_id", "")

    if request.method == "POST":
        custom_name = request.form.get("custom_name", "").strip()
        vessel_voyage = request.form.get("vessel_voyage", "").strip()
        bl_no = request.form.get("bl_no", "").strip()
        shipping_company = request.form.get("shipping_company", "").strip()
        etd = request.form.get("etd", "").strip()
        destination = request.form.get("destination", "").strip()
        cutoff_time = request.form.get("cutoff_time", "").strip()
        order_id = request.form.get("order_id", type=int)
        status = request.form.get("status", "待订舱")
        remarks = request.form.get("remarks", "").strip()

        if not order_id:
            flash("请选择关联订单", "error")
            return render_template(
                "booking/form.html",
                active_menu="booking",
                booking=None,
                orders=orders,
                selected_order_id=selected_order_id,
            )

        if not vessel_voyage and not shipping_company:
            flash("请至少填写航名/航次或船公司", "error")
            return render_template(
                "booking/form.html",
                active_menu="booking",
                booking=None,
                orders=orders,
                selected_order_id=selected_order_id,
            )

        br = BookingRecord(
            custom_name=custom_name,
            vessel_voyage=vessel_voyage,
            bl_no=bl_no,
            shipping_company=shipping_company,
            etd=datetime.strptime(etd, "%Y-%m-%d").date() if etd else None,
            destination=destination,
            cutoff_time=cutoff_time,
            order_id=order_id,
            status=status,
            remarks=remarks,
        )
        db.session.add(br)

        # 同步订单状态
        order = db.session.get(Order, order_id)
        if order and order.status in ("下单", "生产中", "生产完成"):
            if status in ("已订舱", "已出运"):
                order.status = "已订舱"
            else:
                order.status = "订舱中"

        db.session.commit()
        flash("订舱记录创建成功", "success")
        return redirect(url_for("booking.list_booking"))

    return render_template(
        "booking/form.html",
        active_menu="booking",
        booking=None,
        orders=orders,
        selected_order_id=selected_order_id,
    )


@booking_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_booking(id):
    booking = db.session.get(BookingRecord, id)
    if not booking:
        flash("订舱记录不存在", "error")
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
        booking.status = request.form.get("status", "待订舱")
        booking.remarks = request.form.get("remarks", "").strip()

        if not booking.order_id:
            flash("请选择关联订单", "error")
            return render_template(
                "booking/form.html",
                active_menu="booking",
                booking=booking,
                orders=orders,
                selected_order_id=str(booking.order_id) if booking.order_id else "",
            )

        # 同步订单状态
        order = db.session.get(Order, booking.order_id)
        if order:
            if booking.status == "已出运" and order.status != "装柜完成":
                order.status = "已订舱"
            elif booking.status == "已订舱":
                order.status = "已订舱"
            elif order.status not in ("已订舱", "装柜完成", "已出运", "已取消"):
                order.status = "订舱中"

        db.session.commit()
        flash("订舱记录更新成功", "success")
        return redirect(url_for("booking.list_booking"))

    return render_template(
        "booking/form.html",
        active_menu="booking",
        booking=booking,
        orders=orders,
        selected_order_id=str(booking.order_id) if booking.order_id else "",
    )


@booking_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_booking(id):
    br = db.session.get(BookingRecord, id)
    if not br:
        flash("订舱记录不存在", "error")
        return redirect(url_for("booking.list_booking"))

    db.session.delete(br)
    db.session.commit()
    flash("订舱记录已删除", "success")
    return redirect(url_for("booking.list_booking"))
