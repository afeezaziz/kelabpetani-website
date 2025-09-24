from flask import render_template, redirect, url_for, session, flash, request, abort
from sqlalchemy.orm import selectinload
from decimal import Decimal
import bleach

from app.blueprint import main
from app.extensions import db, limiter
from app.models import User, PawahProject, AuditLog
from app.utils.decorators import login_required
from app.utils.notifications import safe_send_email


PAWAH_TRANSITIONS = {
    'accepted': {'in_progress', 'completed', 'cancelled'},
    'in_progress': {'completed', 'cancelled'},
}


@main.route('/pawah')
def pawah_list():
    q = request.args.get('q', '').strip()
    crop_type = request.args.get('crop_type', '').strip()
    location = request.args.get('location', '').strip()
    status = request.args.get('status', '').strip()
    page = request.args.get('page', default=1, type=int)

    query = PawahProject.query.filter(PawahProject.is_approved.is_(True))

    if q:
        like = f"%{q}%"
        query = query.filter((PawahProject.title.ilike(like)) | (PawahProject.description.ilike(like)))
    if crop_type:
        query = query.filter(PawahProject.crop_type == crop_type)
    if location:
        query = query.filter(PawahProject.location == location)
    if status:
        query = query.filter(PawahProject.status == status)

    query = query.order_by(PawahProject.created_at.desc())
    pagination = db.paginate(query, page=page, per_page=12, error_out=False)

    return render_template(
        'pawah_list.html',
        pagination=pagination,
        projects=pagination.items,
        q=q,
        crop_type=crop_type,
        location=location,
        status=status,
    )


@main.route('/pawah/new', methods=['GET', 'POST'])
@login_required
def pawah_new():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        crop_type = request.form.get('crop_type', '').strip()
        location = request.form.get('location', '').strip()
        duration_months = int(request.form.get('duration_months', '0'))
        capital_required = request.form.get('capital_required', '0').strip()
        owner_share_percent = int(request.form.get('owner_share_percent', '50'))
        farmer_share_percent = int(request.form.get('farmer_share_percent', '50'))

        if not title or not crop_type or not location or duration_months <= 0:
            flash('Sila lengkapkan maklumat yang diperlukan.', 'error')
            return render_template('pawah_new.html')

        if owner_share_percent + farmer_share_percent != 100:
            flash('Jumlah peratusan kongsi mesti 100%.', 'error')
            return render_template('pawah_new.html')

        try:
            project = PawahProject(
                title=title,
                description=description,
                crop_type=crop_type,
                location=location,
                duration_months=duration_months,
                capital_required=Decimal(capital_required),
                owner_share_percent=owner_share_percent,
                farmer_share_percent=farmer_share_percent,
                status='open',
                is_approved=False,
                owner_id=session['user_id']
            )
            db.session.add(project)
            db.session.commit()
            flash('Projek pawah dihantar untuk semakan admin. Ia akan dipaparkan selepas diluluskan.', 'success')
            return redirect(url_for('main.pawah_list'))
        except Exception:
            db.session.rollback()
            flash('Ralat semasa mencipta projek.', 'error')
            return render_template('pawah_new.html')

    return render_template('pawah_new.html')


@main.route('/pawah/<int:project_id>', methods=['GET'])
def pawah_detail(project_id):
    project = PawahProject.query.get_or_404(project_id)
    # Allow admin or participants to view unapproved project
    if not project.is_approved and not (session.get('is_admin') or (session.get('user_id') and session['user_id'] in [project.owner_id, project.farmer_id])):
        abort(404)
    owner = User.query.get(project.owner_id) if project.owner_id else None
    farmer = User.query.get(project.farmer_id) if project.farmer_id else None
    from app.models import Message
    messages = (
        Message.query.options(selectinload(Message.sender))
        .filter_by(context_type='pawah', context_id=project.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    return render_template('pawah_detail.html', project=project, owner=owner, farmer=farmer, messages=messages)


@main.route('/pawah/<int:project_id>/accept', methods=['POST'])
@login_required
@limiter.limit('10 per minute', methods=['POST'])
def pawah_accept(project_id):
    if 'user_id' not in session:
        flash('Sila log masuk untuk menerima projek.', 'error')
        return redirect(url_for('main.login'))

    project = PawahProject.query.get_or_404(project_id)
    if project.status != 'open':
        flash('Projek ini tidak lagi dibuka.', 'error')
        return redirect(url_for('main.pawah_detail', project_id=project.id))

    if project.owner_id == session['user_id']:
        flash('Anda tidak boleh menerima projek anda sendiri.', 'error')
        return redirect(url_for('main.pawah_detail', project_id=project.id))

    try:
        project.farmer_id = session['user_id']
        old_status = project.status
        project.status = 'accepted'
        db.session.add(AuditLog(entity_type='pawah', entity_id=project.id, action='accept', old_status=old_status, new_status=project.status, actor_id=session['user_id']))
        db.session.commit()
        flash('Anda telah menerima projek ini. Hubungi pemilik untuk langkah seterusnya.', 'success')
        # Notify owner
        owner = User.query.get(project.owner_id)
        if owner and owner.email:
            safe_send_email(owner.email, f"Pawah #{project.id}: Projek diterima", f"Projek '{project.title}' telah diterima oleh seorang petani.")
    except Exception:
        db.session.rollback()
        flash('Ralat semasa menerima projek.', 'error')

    return redirect(url_for('main.pawah_detail', project_id=project.id))


@main.route('/pawah/<int:project_id>/message', methods=['POST'])
@login_required
@limiter.limit('30 per minute', methods=['POST'])
def pawah_add_message(project_id):
    from app.models import Message
    project = PawahProject.query.get_or_404(project_id)
    user_id = session['user_id']
    if user_id not in [project.owner_id, project.farmer_id]:
        abort(403)
    content = request.form.get('content', '').strip()
    if not content:
        flash('Mesej tidak boleh kosong.', 'error')
        return redirect(url_for('main.pawah_detail', project_id=project.id))
    if len(content) > 1000:
        flash('Mesej terlalu panjang (maksimum 1000 aksara).', 'error')
        return redirect(url_for('main.pawah_detail', project_id=project.id))
    sanitized = bleach.clean(content, tags=[], strip=True)
    msg = Message(context_type='pawah', context_id=project.id, sender_id=user_id, content=sanitized)
    db.session.add(msg)
    db.session.commit()
    # Notify the other participant
    if user_id == project.owner_id and project.farmer_id:
        farmer = User.query.get(project.farmer_id)
        if farmer and farmer.email:
            safe_send_email(farmer.email, f"Pawah #{project.id}: Mesej baru", sanitized)
    elif user_id == project.farmer_id:
        owner = User.query.get(project.owner_id)
        if owner and owner.email:
            safe_send_email(owner.email, f"Pawah #{project.id}: Mesej baru", sanitized)
    return redirect(url_for('main.pawah_detail', project_id=project.id))


@main.route('/pawah/<int:project_id>/start', methods=['POST'])
@login_required
@limiter.limit('20 per minute', methods=['POST'])
def pawah_start(project_id):
    project = PawahProject.query.get_or_404(project_id)
    user_id = session['user_id']
    if user_id not in [project.owner_id, project.farmer_id]:
        abort(403)
    allowed = PAWAH_TRANSITIONS.get(project.status, set())
    if 'in_progress' not in allowed:
        abort(403)
    old_status = project.status
    project.status = 'in_progress'
    db.session.add(AuditLog(entity_type='pawah', entity_id=project.id, action='status_change', old_status=old_status, new_status='in_progress', actor_id=user_id))
    db.session.commit()
    # Notify both participants
    for uid in [project.owner_id, project.farmer_id]:
        if uid:
            user = User.query.get(uid)
            if user and user.email:
                safe_send_email(user.email, f"Pawah #{project.id}: Dimulakan", f"Projek '{project.title}' kini bermula.")
    flash('Projek dimulakan.', 'success')
    return redirect(url_for('main.pawah_detail', project_id=project.id))


@main.route('/pawah/<int:project_id>/complete', methods=['POST'])
@login_required
@limiter.limit('20 per minute', methods=['POST'])
def pawah_complete(project_id):
    project = PawahProject.query.get_or_404(project_id)
    user_id = session['user_id']
    if user_id not in [project.owner_id, project.farmer_id]:
        abort(403)
    allowed = PAWAH_TRANSITIONS.get(project.status, set())
    if 'completed' not in allowed:
        abort(403)
    old_status = project.status
    project.status = 'completed'
    db.session.add(AuditLog(entity_type='pawah', entity_id=project.id, action='status_change', old_status=old_status, new_status='completed', actor_id=user_id))
    db.session.commit()
    for uid in [project.owner_id, project.farmer_id]:
        if uid:
            user = User.query.get(uid)
            if user and user.email:
                safe_send_email(user.email, f"Pawah #{project.id}: Selesai", f"Projek '{project.title}' telah selesai.")
    flash('Projek ditandakan selesai.', 'success')
    return redirect(url_for('main.pawah_detail', project_id=project.id))


@main.route('/pawah/<int:project_id>/cancel', methods=['POST'])
@login_required
@limiter.limit('20 per minute', methods=['POST'])
def pawah_cancel(project_id):
    project = PawahProject.query.get_or_404(project_id)
    user_id = session['user_id']
    if user_id not in [project.owner_id, project.farmer_id]:
        abort(403)
    allowed = PAWAH_TRANSITIONS.get(project.status, set())
    if 'cancelled' not in allowed:
        abort(403)
    old_status = project.status
    project.status = 'cancelled'
    db.session.add(AuditLog(entity_type='pawah', entity_id=project.id, action='status_change', old_status=old_status, new_status='cancelled', actor_id=user_id))
    db.session.commit()
    for uid in [project.owner_id, project.farmer_id]:
        if uid:
            user = User.query.get(uid)
            if user and user.email:
                safe_send_email(user.email, f"Pawah #{project.id}: Dibatalkan", f"Projek '{project.title}' telah dibatalkan.")
    flash('Projek dibatalkan.', 'success')
    return redirect(url_for('main.pawah_detail', project_id=project.id))
