from flask import render_template, redirect, url_for, session, flash, request, abort
from app.blueprint import main
from app.extensions import db, limiter
from app.models import Product, Order
from app.utils.decorators import login_required
from decimal import Decimal
from sqlalchemy import or_


@main.route('/marketplace')
def marketplace():
    # Filters
    q = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip()
    location = request.args.get('location', '').strip()
    min_price = request.args.get('min_price', '').strip()
    max_price = request.args.get('max_price', '').strip()
    page = request.args.get('page', default=1, type=int)

    query = Product.query.filter(Product.is_active.is_(True), Product.is_approved.is_(True))

    if q:
        like = f"%{q}%"
        query = query.filter(or_(Product.title.ilike(like), Product.description.ilike(like)))
    if category:
        query = query.filter(Product.category == category)
    if location:
        query = query.filter(Product.location == location)
    if min_price:
        try:
            query = query.filter(Product.price >= Decimal(min_price))
        except Exception:
            pass
    if max_price:
        try:
            query = query.filter(Product.price <= Decimal(max_price))
        except Exception:
            pass

    query = query.order_by(Product.created_at.desc())
    pagination = db.paginate(query, page=page, per_page=12, error_out=False)

    return render_template(
        'marketplace_list.html',
        pagination=pagination,
        products=pagination.items,
        q=q,
        category=category,
        location=location,
        min_price=min_price,
        max_price=max_price,
    )


@main.route('/marketplace/new', methods=['GET', 'POST'])
def new_product():
    if 'user_id' not in session:
        flash('Sila log masuk untuk menambah produk.', 'error')
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        price = request.form.get('price', '').strip()
        quantity = request.form.get('quantity', '1').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        image_url = request.form.get('image_url', '').strip()
        location = request.form.get('location', '').strip()
        unit = request.form.get('unit', '').strip()
        min_order_qty = request.form.get('min_order_qty', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()

        if not title or not price:
            flash('Tajuk dan harga diperlukan.', 'error')
            return render_template('marketplace_new.html')

        try:
            product = Product(
                title=title,
                price=Decimal(price),
                quantity=int(quantity or 1),
                description=description,
                category=category,
                image_url=image_url or None,
                location=location or None,
                unit=unit or None,
                min_order_qty=int(min_order_qty) if min_order_qty else None,
                contact_phone=contact_phone or None,
                is_approved=False,
                seller_id=session['user_id']
            )
            db.session.add(product)
            db.session.commit()
            flash('Produk dihantar untuk semakan admin. Ia akan dipaparkan selepas diluluskan.', 'success')
            return redirect(url_for('main.marketplace'))
        except Exception:
            db.session.rollback()
            flash('Ralat menambah produk. Sila cuba lagi.', 'error')
            return render_template('marketplace_new.html')

    return render_template('marketplace_new.html')


@main.route('/marketplace/<int:product_id>', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    viewer_id = session.get('user_id')
    is_owner = viewer_id and (product.seller_id == viewer_id)
    is_admin = session.get('is_admin')
    if (not product.is_active or not product.is_approved) and not (is_owner or is_admin):
        abort(404)

    if request.method == 'POST':
        if 'user_id' not in session:
            flash('Sila log masuk untuk membeli.', 'error')
            return redirect(url_for('main.login'))

        if is_owner:
            flash('Anda tidak boleh membeli produk anda sendiri.', 'error')
            return redirect(url_for('main.product_detail', product_id=product.id))

        qty = int(request.form.get('quantity', '1'))
        if qty < 1:
            flash('Kuantiti tidak sah.', 'error')
            return redirect(url_for('main.product_detail', product_id=product.id))

        if product.min_order_qty and qty < product.min_order_qty:
            flash(f'Minimum pesanan ialah {product.min_order_qty}.', 'error')
            return redirect(url_for('main.product_detail', product_id=product.id))

        if product.quantity is not None and product.quantity < qty:
            flash('Stok tidak mencukupi.', 'error')
            return redirect(url_for('main.product_detail', product_id=product.id))

        try:
            total_price = product.price * Decimal(qty)
            # Atomic stock decrement when quantity-limited
            if product.quantity is not None:
                updated = (
                    db.session.query(Product)
                    .filter(Product.id == product.id, Product.quantity >= qty)
                    .update({Product.quantity: Product.quantity - qty}, synchronize_session=False)
                )
                if updated == 0:
                    db.session.rollback()
                    flash('Stok tidak mencukupi.', 'error')
                    return redirect(url_for('main.product_detail', product_id=product.id))

            order = Order(
                buyer_id=session['user_id'],
                product_id=product.id,
                quantity=qty,
                total_price=total_price,
                status='pending'
            )
            db.session.add(order)
            db.session.commit()
            flash('Pesanan dibuat. Anda boleh berhubung dengan penjual melalui halaman pesanan.', 'success')
            return redirect(url_for('main.order_detail', order_id=order.id))
        except Exception:
            db.session.rollback()
            flash('Ralat semasa membuat pesanan.', 'error')

        return redirect(url_for('main.product_detail', product_id=product.id))

    return render_template('marketplace_detail.html', product=product)


@main.route('/marketplace/my')
@login_required
def my_listings():
    user_id = session['user_id']
    products = (
        Product.query.filter_by(seller_id=user_id)
        .order_by(Product.created_at.desc())
        .all()
    )
    return render_template('marketplace_my.html', products=products)


@main.route('/marketplace/<int:product_id>/archive', methods=['POST'])
@login_required
@limiter.limit('10 per minute', methods=['POST'])
def product_archive(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != session['user_id']:
        abort(403)
    product.is_active = False
    db.session.commit()
    flash('Produk diarkibkan.', 'success')
    return redirect(url_for('main.my_listings'))


@main.route('/marketplace/<int:product_id>/unarchive', methods=['POST'])
@login_required
@limiter.limit('10 per minute', methods=['POST'])
def product_unarchive(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != session['user_id']:
        abort(403)
    product.is_active = True
    db.session.commit()
    flash('Produk diaktifkan semula.', 'success')
    return redirect(url_for('main.my_listings'))


@main.route('/marketplace/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    if product.seller_id != session['user_id']:
        abort(403)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        price = request.form.get('price', '').strip()
        quantity = request.form.get('quantity', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        image_url = request.form.get('image_url', '').strip()
        location = request.form.get('location', '').strip()
        unit = request.form.get('unit', '').strip()
        min_order_qty = request.form.get('min_order_qty', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()

        if not title or not price:
            flash('Tajuk dan harga diperlukan.', 'error')
            return render_template('marketplace_edit.html', product=product)

        try:
            product.title = title
            product.price = Decimal(price)
            product.quantity = int(quantity) if quantity != '' else None
            product.description = description or None
            product.category = category or None
            product.image_url = image_url or None
            product.location = location or None
            product.unit = unit or None
            product.min_order_qty = int(min_order_qty) if min_order_qty else None
            product.contact_phone = contact_phone or None
            product.is_approved = False
            product.rejection_reason = None
            product.approved_at = None
            product.reviewed_by_id = None
            product.reviewed_at = None
            db.session.commit()
            flash('Produk dikemaskini dan dihantar untuk kelulusan semula.', 'success')
            return redirect(url_for('main.my_listings'))
        except Exception:
            db.session.rollback()
            flash('Ralat mengemaskini produk.', 'error')
            return render_template('marketplace_edit.html', product=product)

    return render_template('marketplace_edit.html', product=product)
