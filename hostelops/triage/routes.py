"""Triage and analytics routes for HostelOps (Module 3)."""
from flask import jsonify, render_template, request
from flask_login import current_user

from hostelops.auth.decorators import roles_required
from hostelops.models import CATEGORIES, STATUSES, Complaint, utcnow
from hostelops.triage import triage_bp
from hostelops.triage import predictor  # import module to avoid name clash
from hostelops.triage.overdue import is_overdue


# ---------------------------------------------------------------------------
# Part B: suggest API
# ---------------------------------------------------------------------------

@triage_bp.route('/api/triage/suggest', methods=['POST'])
def suggest():
    """POST /api/triage/suggest — predict category and priority from text."""
    if not current_user.is_authenticated:
        return jsonify(error='Authentication required'), 401

    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get('text'), str):
        return jsonify(error='JSON body with a "text" string is required'), 400

    category, priority, confidence = predictor.suggest(body['text'])
    return jsonify(category=category, priority=priority, confidence=confidence)


# ---------------------------------------------------------------------------
# Part C: stats API and dashboard
# ---------------------------------------------------------------------------

def _collect_stats():
    """Load all complaints and compute aggregated stats.

    Returns a dict with by_category, by_status, overdue_count, and
    overdue_list (each item has id, title, category, status, hours_open).
    """
    complaints = Complaint.query.all()
    now = utcnow()

    # Count by category, zero-fill for every known category
    by_category = {cat: 0 for cat in CATEGORIES}
    for c in complaints:
        if c.category in by_category:
            by_category[c.category] += 1

    # Count by status, zero-fill for every known status
    by_status = {s: 0 for s in STATUSES}
    for c in complaints:
        if c.status in by_status:
            by_status[c.status] += 1

    # Overdue complaints
    overdue_list = []
    for c in complaints:
        if is_overdue(c, now=now):
            age_hours = int((now - c.created_at).total_seconds() // 3600)
            overdue_list.append({
                'id': c.id,
                'title': c.title,
                'category': c.category,
                'status': c.status,
                'hours_open': age_hours,
            })

    return {
        'by_category': by_category,
        'by_status': by_status,
        'overdue_count': len(overdue_list),
        'overdue_list': overdue_list,
    }


@triage_bp.route('/api/stats', methods=['GET'])
def stats():
    """GET /api/stats — aggregate complaint stats (staff/admin only)."""
    if not current_user.is_authenticated:
        return jsonify(error='Authentication required'), 401

    if getattr(current_user, 'role', None) not in ('staff', 'admin'):
        return jsonify(error='Forbidden: staff or admin role required'), 403

    data = _collect_stats()
    return jsonify(
        by_category=data['by_category'],
        by_status=data['by_status'],
        overdue=data['overdue_count'],
    )


@triage_bp.route('/dashboard', methods=['GET'])
@roles_required('staff', 'admin')
def dashboard():
    """GET /dashboard — analytics dashboard (staff/admin only)."""
    data = _collect_stats()
    return render_template(
        'triage/dashboard.html',
        overdue_count=data['overdue_count'],
        overdue_list=data['overdue_list'],
    )
