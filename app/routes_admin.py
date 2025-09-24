from flask import render_template, redirect, url_for, session, flash, request
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.blueprint import main
from app.extensions import db, limiter
from app.models import User, Product, PawahProject, AuditLog
from app.utils.decorators import admin_required
from app.utils.notifications import safe_send_email


@main.route('/admin')
@admin_required
def admin_home():
    pending_products = Product.query.filter_by(is_approved=False).order_by(Product.created_at.desc()).all()
    pending_projects = PawahProject.query.filter_by(is_approved=False).order_by(PawahProject.created_at.desc()).all()
    return render_template('admin_home.html', pending_products=pending_products, pending_projects=pending_projects)


@main.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin_products.html', products=products)


@main.route('/admin/pawah')
@admin_required
def admin_pawah():
    projects = PawahProject.query.order_by(PawahProject.created_at.desc()).all()
    return render_template('admin_pawah.html', projects=projects)


@main.route('/admin/products/<int:product_id>/approve', methods=['POST'])
@admin_required
@limiter.limit('20 per minute', methods=['POST'])
def admin_approve_product(product_id):
    product = Product.query.get_or_404(product_id)
    approve = request.form.get('approve') == 'true'
    reason = request.form.get('reason', '').strip()
    user = User.query.get(session.get('user_id'))
    now = datetime.utcnow()

    if approve:
        product.is_approved = True
        product.rejection_reason = None
        product.approved_at = now
    else:
        product.is_approved = False
        product.rejection_reason = reason or None
        product.approved_at = None
    product.reviewed_by_id = user.id if user else None
    product.reviewed_at = now

    action = 'approve' if approve else 'reject'
    db.session.add(AuditLog(entity_type='product', entity_id=product.id, action=action, actor_id=(user.id if user else None), meta=(reason or None)))
    db.session.commit()

    # Notify seller
    seller = User.query.get(product.seller_id)
    if seller and seller.email:
        status_text = 'diluluskan' if approve else 'ditolak'
        body = f"Produk '{product.title}' {status_text}." + (f" Sebab: {reason}" if reason else '')
        safe_send_email(seller.email, f"Produk #{product.id}: {status_text}", body)

    return redirect(request.referrer or url_for('main.admin_products'))


@main.route('/admin/pawah/<int:project_id>/approve', methods=['POST'])
@admin_required
@limiter.limit('20 per minute', methods=['POST'])
def admin_approve_pawah(project_id):
    project = PawahProject.query.get_or_404(project_id)
    approve = request.form.get('approve') == 'true'
    reason = request.form.get('reason', '').strip()
    user = User.query.get(session.get('user_id'))
    now = datetime.utcnow()

    if approve:
        project.is_approved = True
        project.rejection_reason = None
        project.approved_at = now
    else:
        project.is_approved = False
        project.rejection_reason = reason or None
        project.approved_at = None
    project.reviewed_by_id = user.id if user else None
    project.reviewed_at = now

    action = 'approve' if approve else 'reject'
    db.session.add(AuditLog(entity_type='pawah', entity_id=project.id, action=action, actor_id=(user.id if user else None), meta=(reason or None)))
    db.session.commit()

    # Notify owner
    owner = User.query.get(project.owner_id)
    if owner and owner.email:
        status_text = 'diluluskan' if approve else 'ditolak'
        body = f"Projek pawah '{project.title}' {status_text}." + (f" Sebab: {reason}" if reason else '')
        safe_send_email(owner.email, f"Pawah #{project.id}: {status_text}", body)

    return redirect(request.referrer or url_for('main.admin_pawah'))


@main.route('/admin/logs')
@admin_required
def admin_logs():
    entity_type = request.args.get('entity_type', '').strip()
    action = request.args.get('action', '').strip()
    actor_id = request.args.get('actor_id', type=int)
    page = request.args.get('page', default=1, type=int)

    query = AuditLog.query.options(selectinload(AuditLog.actor))
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AuditLog.action == action)
    if actor_id:
        query = query.filter(AuditLog.actor_id == actor_id)

    query = query.order_by(AuditLog.created_at.desc())
    pagination = db.paginate(query, page=page, per_page=20, error_out=False)
    entity_types = ['order', 'pawah', 'product']
    actions = ['status_change', 'approve', 'reject', 'accept']
    return render_template('admin_logs.html', pagination=pagination, logs=pagination.items, entity_type=entity_type, action=action, actor_id=actor_id, entity_types=entity_types, actions=actions)
