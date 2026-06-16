from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from models import db, Order, ProductionTask
from datetime import datetime

production_bp = Blueprint("production", __name__, url_prefix="/production")


@production_bp.route("/")
@login_required
def list_production():
    current_status = request.args.get("status", "").strip()
    page = request.args.get("page", 1, type=int)

    query = ProductionTask.query

    if current_status and current_status in ("待生产", "生产中", "已完成"):
        query = query.filter(ProductionTask.status == current_status)

    query = query.order_by(db.desc(ProductionTask.id))
    pagination = query.paginate(page=page, per_page=15, error_out=False)
    production_tasks = pagination.items

    return render_template(
        "production/list.html",
        active_menu="production",
        production_tasks=production_tasks,
        current_status=current_status,
    )


@production_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_production():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    selected_order_id = request.args.get("order_id", "")

    if request.method == "POST":
        order_id = request.form.get("order_id", type=int)
        start_date = request.form.get("start_date", "")
        expected_end_date = request.form.get("expected_end_date", "")
        actual_end_date = request.form.get("actual_end_date", "")
        status = request.form.get("status", "待生产")
        remarks = request.form.get("remarks", "").strip()

        if not order_id:
            flash("请选择关联订单", "error")
            return render_template(
                "production/form.html",
                active_menu="production",
                task=None,
                orders=orders,
                selected_order_id=selected_order_id,
            )

        order = db.session.get(Order, order_id)
        if not order:
            flash("所选订单不存在", "error")
            return redirect(url_for("production.list_production"))

        task = ProductionTask(
            order_id=order_id,
            start_date=datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None,
            expected_end_date=datetime.strptime(expected_end_date, "%Y-%m-%d").date() if expected_end_date else None,
            actual_end_date=datetime.strptime(actual_end_date, "%Y-%m-%d").date() if actual_end_date else None,
            status=status,
            remarks=remarks,
        )
        db.session.add(task)

        # 如果订单状态还是"下单"，推进为"生产中"
        if order.status == "下单" and status in ("生产中", "已完成"):
            order.status = "生产中"

        db.session.commit()
        flash("生产任务创建成功", "success")
        return redirect(url_for("production.list_production"))

    return render_template(
        "production/form.html",
        active_menu="production",
        task=None,
        orders=orders,
        selected_order_id=selected_order_id,
    )


@production_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_production(id):
    task = db.session.get(ProductionTask, id)
    if not task:
        flash("生产任务不存在", "error")
        return redirect(url_for("production.list_production"))

    orders = Order.query.order_by(Order.created_at.desc()).all()

    if request.method == "POST":
        order_id = request.form.get("order_id", type=int)
        start_date = request.form.get("start_date", "")
        expected_end_date = request.form.get("expected_end_date", "")
        actual_end_date = request.form.get("actual_end_date", "")
        status = request.form.get("status", "待生产")
        remarks = request.form.get("remarks", "").strip()

        if not order_id:
            flash("请选择关联订单", "error")
            return render_template(
                "production/form.html",
                active_menu="production",
                task=task,
                orders=orders,
                selected_order_id="",
            )

        task.order_id = order_id
        task.start_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        task.expected_end_date = datetime.strptime(expected_end_date, "%Y-%m-%d").date() if expected_end_date else None
        task.actual_end_date = datetime.strptime(actual_end_date, "%Y-%m-%d").date() if actual_end_date else None
        task.status = status
        task.remarks = remarks

        # 同步更新订单状态
        order = db.session.get(Order, order_id)
        if order and order.status == "下单" and status in ("生产中", "已完成"):
            order.status = "生产中"
        if order and status == "已完成" and order.status in ("下单", "生产中"):
            order.status = "生产完成"

        db.session.commit()
        flash("生产任务更新成功", "success")
        return redirect(url_for("production.list_production"))

    return render_template(
        "production/form.html",
        active_menu="production",
        task=task,
        orders=orders,
        selected_order_id=str(task.order_id),
    )


@production_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete_production(id):
    task = db.session.get(ProductionTask, id)
    if not task:
        flash("生产任务不存在", "error")
        return redirect(url_for("production.list_production"))

    db.session.delete(task)
    db.session.commit()
    flash("生产任务已删除", "success")
    return redirect(url_for("production.list_production"))
