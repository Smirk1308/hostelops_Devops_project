"""Complaint creation, viewing, and management routes."""
from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select

from hostelops.auth.decorators import roles_required
from hostelops.complaints import complaints_bp
from hostelops.extensions import db
from hostelops.models import CATEGORIES, PRIORITIES, STATUSES, Complaint, User, utcnow
from hostelops.triage.overdue import is_overdue


def _get_complaint_or_404(complaint_id):
    """Return a complaint or raise the standard 404 response."""
    complaint = db.session.get(Complaint, complaint_id)
    if complaint is None:
        abort(404)
    return complaint


def _validate_complaint_form():
    """Return cleaned values and field errors for a complaint form."""
    values = {
        'title': request.form.get('title', '').strip(),
        'description': request.form.get('description', '').strip(),
        'category': request.form.get('category', '').strip(),
        'priority': request.form.get('priority', 'Medium').strip(),
    }
    errors = {}
    if not values['title']:
        errors['title'] = 'Enter a title.'
    elif len(values['title']) > 150:
        errors['title'] = 'Title must be 150 characters or fewer.'
    if not values['description']:
        errors['description'] = 'Describe the issue.'
    if values['category'] not in CATEGORIES:
        errors['category'] = 'Choose a valid category.'
    if values['priority'] not in PRIORITIES:
        errors['priority'] = 'Choose a valid priority.'
    return values, errors


@complaints_bp.route('/')
def index():
    """Send the home route to the complaint workspace."""
    return redirect(url_for('complaints.list_complaints'))


@complaints_bp.route('/complaints')
@login_required
def list_complaints():
    """Show accessible complaints, filters, and unfiltered status totals."""
    query = select(Complaint)
    totals_query = select(Complaint.status, db.func.count(Complaint.id)).group_by(
        Complaint.status
    )
    if current_user.role == 'student':
        query = query.where(Complaint.created_by == current_user.id)
        totals_query = totals_query.where(Complaint.created_by == current_user.id)

    filters = {
        'status': request.args.get('status', '').strip(),
        'category': request.args.get('category', '').strip(),
        'priority': request.args.get('priority', '').strip(),
    }
    # Students always see their own records and cannot use filters to broaden access.
    if current_user.role in ('staff', 'admin'):
        valid_values = {
            'status': STATUSES,
            'category': CATEGORIES,
            'priority': PRIORITIES,
        }
        for field, choices in valid_values.items():
            if filters[field] in choices:
                query = query.where(getattr(Complaint, field) == filters[field])
            else:
                filters[field] = ''

    complaints = db.session.scalars(
        query.order_by(Complaint.created_at.desc(), Complaint.id.desc())
    ).all()
    totals = dict(db.session.execute(totals_query).all())
    counts = {status: totals.get(status, 0) for status in STATUSES}
    overdue_ids = {item.id for item in complaints if is_overdue(item)}
    staff_users = []
    return render_template(
        'complaints/list.html', complaints=complaints, counts=counts,
        filters=filters, categories=CATEGORIES, priorities=PRIORITIES,
        statuses=STATUSES, overdue_ids=overdue_ids,
        matching_count=len(complaints), staff_users=staff_users,
    )


@complaints_bp.route('/complaints/new', methods=['GET', 'POST'])
@login_required
def new_complaint():
    """Create a complaint submitted by the signed-in user."""
    values = {'title': '', 'description': '', 'category': '', 'priority': 'Medium'}
    errors = {}
    if request.method == 'POST':
        values, errors = _validate_complaint_form()
        if not errors:
            complaint = Complaint(
                title=values['title'], description=values['description'],
                category=values['category'], priority=values['priority'],
                status='Pending', created_by=current_user.id, assigned_to=None,
                resolved_at=None,
            )
            db.session.add(complaint)
            db.session.commit()
            flash('Your complaint has been submitted.', 'success')
            return redirect(url_for('complaints.detail', complaint_id=complaint.id))
    return render_template(
        'complaints/new.html', values=values, errors=errors,
        categories=CATEGORIES, priorities=PRIORITIES,
    )


@complaints_bp.route('/complaints/<int:complaint_id>')
@login_required
def detail(complaint_id):
    """Show a complaint to its owner or to staff and administrators."""
    complaint = _get_complaint_or_404(complaint_id)
    if current_user.role == 'student' and complaint.created_by != current_user.id:
        abort(403)
    managers = current_user.role in ('staff', 'admin')
    staff_users = db.session.scalars(
        select(User).where(User.role.in_(('staff', 'admin'))).order_by(User.name)
    ).all() if managers else []
    return render_template(
        'complaints/detail.html', complaint=complaint,
        overdue=is_overdue(complaint), staff_users=staff_users,
    )


@complaints_bp.route('/complaints/<int:complaint_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_complaint(complaint_id):
    """Edit a pending complaint owned by the current student."""
    complaint = _get_complaint_or_404(complaint_id)
    if (current_user.role != 'student' or complaint.created_by != current_user.id
            or complaint.status != 'Pending'):
        abort(403)
    values = {key: getattr(complaint, key) for key in
              ('title', 'description', 'category', 'priority')}
    errors = {}
    if request.method == 'POST':
        values, errors = _validate_complaint_form()
        if not errors:
            for key, value in values.items():
                setattr(complaint, key, value)
            db.session.commit()
            flash('Your complaint has been updated.', 'success')
            return redirect(url_for('complaints.detail', complaint_id=complaint.id))
    return render_template(
        'complaints/edit.html', complaint=complaint, values=values,
        errors=errors, categories=CATEGORIES, priorities=PRIORITIES,
    )


@complaints_bp.route('/complaints/<int:complaint_id>/delete', methods=['POST'])
@login_required
def delete_complaint(complaint_id):
    """Delete a pending owned complaint or any complaint as an administrator."""
    complaint = _get_complaint_or_404(complaint_id)
    permitted = current_user.role == 'admin' or (
        current_user.role == 'student' and complaint.created_by == current_user.id
        and complaint.status == 'Pending'
    )
    if not permitted:
        abort(403)
    db.session.delete(complaint)
    db.session.commit()
    flash('Complaint deleted.', 'success')
    return redirect(url_for('complaints.list_complaints'))


@complaints_bp.route('/complaints/<int:complaint_id>/assign', methods=['POST'])
@login_required
@roles_required('staff', 'admin')
def assign_complaint(complaint_id):
    """Assign a complaint to a verified staff or administrator account."""
    complaint = _get_complaint_or_404(complaint_id)
    raw_user_id = request.form.get('assigned_to', '').strip()
    assignee = None
    if raw_user_id:
        try:
            assignee_id = int(raw_user_id)
        except ValueError:
            abort(400)
        assignee = db.session.get(User, assignee_id)
        if assignee is None or assignee.role not in ('staff', 'admin'):
            abort(400)
    complaint.assigned_to = assignee.id if assignee else None
    db.session.commit()
    flash('Complaint assignment updated.', 'success')
    return redirect(url_for('complaints.detail', complaint_id=complaint.id))


@complaints_bp.route('/complaints/<int:complaint_id>/status', methods=['POST'])
@login_required
@roles_required('staff', 'admin')
def update_status(complaint_id):
    """Set an allowed complaint status and keep resolved_at consistent."""
    complaint = _get_complaint_or_404(complaint_id)
    status = request.form.get('status', '').strip()
    if status not in STATUSES:
        abort(400)
    complaint.status = status
    complaint.resolved_at = utcnow() if status == 'Resolved' else None
    db.session.commit()
    flash('Complaint status updated.', 'success')
    return redirect(url_for('complaints.detail', complaint_id=complaint.id))


__all__ = [
    'index', 'list_complaints', 'new_complaint', 'detail', 'edit_complaint',
    'delete_complaint', 'assign_complaint', 'update_status',
]
