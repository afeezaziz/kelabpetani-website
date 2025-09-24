from flask import render_template, redirect, url_for, session, flash, request, abort
from sqlalchemy.orm import selectinload
from app.blueprint import main
from app.extensions import db, limiter
from app.models import User, Product, Order, AuditLog
from app.utils.decorators import login_required
from app.utils.notifications import safe_send_email
import bleach


# ----------------------
# Buying flow: Orders
# ----------------------


def _ensure_order_access(order_id):
    order = Order.query.get_or_404(order_id)
    product = Product.query.get(order.product_id)
    user_id = session.get('user_id')
    if not user_id or (order.buyer_id != user_id and product.seller_id != user_id):
        abort(403)
    return order, product


ORDER_TRANSITIONS = {
    'pending': {'paid', 'cancelled'},
    'paid': {'shipped', 'completed'},
    'shipped': {'completed'},
}


@main.route('/orders')
@login_required
def orders_home():
    user_id = session['user_id']
    purchases = (
        Order.query.options(selectinload(Order.product))
        .filter_by(buyer_id=user_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    sales = (
        Order.query.options(selectinload(Order.product), selectinload(Order.buyer))
        .join(Product, Product.id == Order.product_id)
        .filter(Product.seller_id == user_id)
        .order_by(Order.created_at.desc())
        .all()
    )
    return render_template('orders_list.html', purchases=purchases, sales=sales)


@main.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order, product = _ensure_order_access(order_id)
    buyer = User.query.get(order.buyer_id)
    seller = User.query.get(product.seller_id)
    from app.models import Message
    messages = (
        Message.query.options(selectinload(Message.sender))
        .filter_by(context_type='order', context_id=order.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return render_template('order_detail.html', order=order, product=product, buyer=buyer, seller=seller, messages=messages)


@main.route('/orders/<int:order_id>/status', methods=['POST'])
@login_required
@limiter.limit('20 per minute', methods=['POST'])
def order_change_status(order_id):
    action = request.form.get('action')
    order, product = _ensure_order_access(order_id)
    user_id = session['user_id']
    is_seller = (product.seller_id == user_id)

    action_map = {
        'cancel': 'cancelled',
        'mark_paid': 'paid',
        'mark_shipped': 'shipped',
        'mark_completed': 'completed',
    }
    new_status = action_map.get(action)
    if not new_status:
        flash('Tindakan tidak sah.', 'error')
        return redirect(url_for('main.order_detail', order_id=order.id))

    allowed = ORDER_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        abort(403)

    if new_status == 'cancelled':
        if order.buyer_id != user_id:
            abort(403)
    else:
        if not is_seller:
            abort(403)

    try:
        if new_status == 'cancelled' and order.status == 'pending' and product.quantity is not None:
            product.quantity += order.quantity

        old_status = order.status
        order.status = new_status
        db.session.add(AuditLog(entity_type='order', entity_id=order.id, action='status_change', old_status=old_status, new_status=new_status, actor_id=user_id))
        db.session.commit()
        # Notify both parties
        buyer = User.query.get(order.buyer_id)
        seller = User.query.get(product.seller_id)
        subj = f"Pesanan #{order.id}: Status {old_status} -> {new_status}"
        body = f"Status pesanan #{order.id} telah ditukar daripada '{old_status}' kepada '{new_status}'."
        if buyer and buyer.email:
            safe_send_email(buyer.email, subj, body)
        if seller and seller.email:
            safe_send_email(seller.email, subj, body)
        flash('Status pesanan dikemaskini.', 'success')
    except Exception:
        db.session.rollback()
        flash('Ralat mengemas kini pesanan.', 'error')

    return redirect(url_for('main.order_detail', order_id=order.id))


@main.route('/orders/<int:order_id>/message', methods=['POST'])
@login_required
@limiter.limit('30 per minute', methods=['POST'])
def order_add_message(order_id):
    from app.models import Message
    order, product = _ensure_order_access(order_id)
    content = request.form.get('content', '').strip()
    if not content:
        flash('Mesej tidak boleh kosong.', 'error')
        return redirect(url_for('main.order_detail', order_id=order.id))
    if len(content) > 1000:
        flash('Mesej terlalu panjang (maksimum 1000 aksara).', 'error')
        return redirect(url_for('main.order_detail', order_id=order.id))

    sanitized = bleach.clean(content, tags=[], strip=True)
    msg = Message(context_type='order', context_id=order.id, sender_id=session['user_id'], content=sanitized)
    db.session.add(msg)
    db.session.commit()
    # Notify the other party
    buyer = User.query.get(order.buyer_id)
    seller = User.query.get(product.seller_id)
    if session['user_id'] == order.buyer_id and seller and seller.email:
        safe_send_email(seller.email, f"Pesanan #{order.id}: Mesej baru", sanitized)
    elif session['user_id'] == product.seller_id and buyer and buyer.email:
        safe_send_email(buyer.email, f"Pesanan #{order.id}: Mesej baru", sanitized)
    return redirect(url_for('main.order_detail', order_id=order.id))
