"""End-to-end integration tests for HostelOps."""
import re
from datetime import timedelta

from hostelops.extensions import db
from hostelops.models import Complaint, utcnow


def _extract_csrf(html):
    """Extract CSRF token from rendered HTML."""
    match = re.search(r'name=["\']csrf_token["\'] value=["\']([^"\']+)["\']', html)
    if match:
        return match.group(1)
    match_meta = re.search(
        r'name=["\']csrf-token["\'] content=["\']([^"\']+)["\']', html
    )
    if match_meta:
        return match_meta.group(1)
    return ''


def test_complete_complaint_lifecycle_and_analytics(app, client, make_user):
    """Test full workflow: student reports, staff manages, analytics updates."""
    # 1. Create accounts
    student = make_user(
        role='student', email='alice@test.local', password='password123',
        name='Alice Smith', room_no='A-101'
    )
    staff = make_user(
        role='staff', email='bob@test.local', password='password123',
        name='Bob Staff'
    )

    # 2. Student logs in via form
    r_login_page = client.get('/login')
    csrf_token = _extract_csrf(r_login_page.text)
    r_login = client.post('/login', data={
        'csrf_token': csrf_token,
        'email': 'alice@test.local',
        'password': 'password123',
    }, follow_redirects=True)
    assert r_login.status_code == 200
    assert b'Complaints' in r_login.data

    # 3. Triage suggest endpoint
    r_suggest = client.post(
        '/api/triage/suggest',
        json={'text': 'No water in the bathroom tap since morning'},
        headers={'X-CSRFToken': csrf_token},
    )
    assert r_suggest.status_code == 200
    suggest_data = r_suggest.get_json()
    assert 'category' in suggest_data
    assert 'priority' in suggest_data

    # 4. Student creates a complaint
    r_new_page = client.get('/complaints/new')
    csrf_form = _extract_csrf(r_new_page.text)
    r_create = client.post('/complaints/new', data={
        'csrf_token': csrf_form,
        'title': 'Leaking bathroom tap',
        'description': 'Water leaking continuously in room A-101 washroom.',
        'category': 'Water',
        'priority': 'High',
    }, follow_redirects=True)
    assert r_create.status_code == 200
    assert b'Your complaint has been submitted.' in r_create.data

    # Verify complaint in database
    complaint = db.session.scalar(
        db.select(Complaint).where(Complaint.created_by == student.id)
    )
    assert complaint is not None
    assert complaint.status == 'Pending'
    assert complaint.assigned_to is None
    assert complaint.resolved_at is None

    # 5. Student cannot access staff dashboard
    assert client.get('/dashboard').status_code == 403
    assert client.get('/api/stats').status_code == 403

    # 6. Student logs out
    csrf_logout = _extract_csrf(r_create.text)
    r_logout = client.post(
        '/logout', data={'csrf_token': csrf_logout}, follow_redirects=True
    )
    assert r_logout.status_code == 200
    assert b'logged out' in r_logout.data

    # 7. Staff logs in
    r_staff_login_page = client.get('/login')
    csrf_staff = _extract_csrf(r_staff_login_page.text)
    r_staff_login = client.post('/login', data={
        'csrf_token': csrf_staff,
        'email': 'bob@test.local',
        'password': 'password123',
    }, follow_redirects=True)
    assert r_staff_login.status_code == 200
    assert b'Dashboard' in r_staff_login.data

    # 8. Staff views complaints with filter
    r_list = client.get('/complaints?status=Pending&category=Water')
    assert r_list.status_code == 200
    assert b'Leaking bathroom tap' in r_list.data

    # 9. Staff assigns complaint
    r_detail = client.get(f'/complaints/{complaint.id}')
    csrf_detail = _extract_csrf(r_detail.text)
    r_assign = client.post(
        f'/complaints/{complaint.id}/assign',
        data={'csrf_token': csrf_detail, 'assigned_to': str(staff.id)},
        follow_redirects=True,
    )
    assert r_assign.status_code == 200
    db.session.refresh(complaint)
    assert complaint.assigned_to == staff.id

    # 10. Staff updates status to In Progress
    csrf_assign = _extract_csrf(r_assign.text)
    r_status_prog = client.post(
        f'/complaints/{complaint.id}/status',
        data={'csrf_token': csrf_assign, 'status': 'In Progress'},
        follow_redirects=True,
    )
    assert r_status_prog.status_code == 200
    db.session.refresh(complaint)
    assert complaint.status == 'In Progress'
    assert complaint.resolved_at is None

    # 11. Staff resolves complaint
    csrf_prog = _extract_csrf(r_status_prog.text)
    r_resolve = client.post(
        f'/complaints/{complaint.id}/status',
        data={'csrf_token': csrf_prog, 'status': 'Resolved'},
        follow_redirects=True,
    )
    assert r_resolve.status_code == 200
    db.session.refresh(complaint)
    assert complaint.status == 'Resolved'
    assert complaint.resolved_at is not None

    # 12. Staff checks dashboard and stats API
    r_dash = client.get('/dashboard')
    assert r_dash.status_code == 200
    assert b'Operations Dashboard' in r_dash.data

    r_stats = client.get('/api/stats')
    assert r_stats.status_code == 200
    stats = r_stats.get_json()
    assert stats['by_category']['Water'] >= 1
    assert stats['by_status']['Resolved'] >= 1


def test_overdue_detection_integration(app, client, make_user):
    """Test overdue calculation and presentation across detail and stats."""
    make_user(role='staff', email='staff2@test.local')
    student = make_user(role='student', email='student2@test.local')

    # Create an overdue complaint (created 60 hours ago)
    old_time = utcnow() - timedelta(hours=60)
    overdue_complaint = Complaint(
        title='Burst pipe in Block C',
        description='Severe leak flooding corridor',
        category='Water',
        priority='High',
        status='Pending',
        created_by=student.id,
        created_at=old_time,
    )
    db.session.add(overdue_complaint)
    db.session.commit()

    # Log in as staff
    r_login_page = client.get('/login')
    csrf = _extract_csrf(r_login_page.text)
    client.post('/login', data={
        'csrf_token': csrf,
        'email': 'staff2@test.local',
        'password': 'password123',
    }, follow_redirects=True)

    # Check stats API shows overdue
    r_stats = client.get('/api/stats')
    assert r_stats.status_code == 200
    assert r_stats.get_json()['overdue'] >= 1

    # Check complaint detail shows Overdue badge
    r_detail = client.get(f'/complaints/{overdue_complaint.id}')
    assert r_detail.status_code == 200
    assert b'Overdue' in r_detail.data
