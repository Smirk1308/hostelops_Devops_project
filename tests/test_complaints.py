"""Complaint route and workflow tests."""
from datetime import timedelta

import pytest

from hostelops.extensions import db
from hostelops.models import Complaint, utcnow


@pytest.fixture
def make_complaint(app, make_user):
    """Create a complaint with overridable model values."""
    def create(owner=None, **kwargs):
        owner = owner or make_user()
        data = {
            'title': 'Leaking tap',
            'description': 'Water is leaking in the washroom.',
            'category': 'Water',
            'priority': 'Medium',
            'status': 'Pending',
            'created_by': owner.id,
        }
        data.update(kwargs)
        complaint = Complaint(**data)
        db.session.add(complaint)
        db.session.commit()
        return complaint
    return create


def test_index_redirects_to_complaints(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/complaints')


def test_student_list_is_private_and_shows_counts(
        client, make_user, make_complaint, login_as):
    student = make_user(name='Student One')
    other = make_user(name='Student Two')
    own = make_complaint(student)
    make_complaint(other, title='Private complaint')
    make_complaint(student, title='Fixed issue', status='Resolved')
    login_as(client, student)
    response = client.get('/complaints?status=Resolved')
    assert response.status_code == 200
    assert b'Leaking tap' in response.data
    assert b'Private complaint' not in response.data
    assert b'No complaints yet' not in response.data
    assert b'2' in response.data
    assert own.created_by == student.id


@pytest.mark.parametrize('role', ['staff', 'admin'])
def test_manager_list_filters_and_invalid_filters(
    client, make_user, make_complaint, login_as, role
):
    manager = make_user(role=role, name=f'{role} user')
    make_complaint(title='Water pending')
    make_complaint(title='Water fixed', category='Water', status='Resolved')
    make_complaint(title='Furniture pending', category='Furniture')
    login_as(client, manager)
    response = client.get('/complaints?status=Resolved&category=Water&priority=Medium')
    assert response.status_code == 200
    assert b'Water fixed' in response.data
    assert b'Water pending' not in response.data
    assert b'Furniture pending' not in response.data
    response = client.get('/complaints?status=bogus&category=nope&priority=x')
    assert response.status_code == 200
    assert b'Water pending' in response.data


def test_create_complaint_saves_defaults_and_redirects(client, make_user, login_as):
    student = make_user()
    login_as(client, student)
    response = client.post('/complaints/new', data={
        'title': '  Slow drain  ', 'description': '  Drain is blocked  ',
        'category': 'Cleanliness', 'priority': 'Medium',
    })
    assert response.status_code == 302
    complaint = db.session.scalar(db.select(Complaint))
    assert response.headers['Location'].endswith(f'/complaints/{complaint.id}')
    assert (complaint.title, complaint.description, complaint.category) == (
        'Slow drain', 'Drain is blocked', 'Cleanliness')
    assert (complaint.created_by, complaint.status, complaint.priority) == (
        student.id, 'Pending', 'Medium')
    assert complaint.assigned_to is None and complaint.resolved_at is None


@pytest.mark.parametrize(('payload', 'field'), [
    ({'title': '', 'description': 'Issue', 'category': 'Water',
      'priority': 'Low'}, 'title'),
    ({'title': 'x' * 151, 'description': 'Issue', 'category': 'Water',
      'priority': 'Low'}, 'title'),
    ({'title': 'Issue', 'description': ' ', 'category': 'Water',
      'priority': 'Low'}, 'description'),
    ({'title': 'Issue', 'description': 'Issue', 'category': 'Fake',
      'priority': 'Low'}, 'category'),
    ({'title': 'Issue', 'description': 'Issue', 'category': 'Water',
      'priority': 'Urgent'}, 'priority'),
])
def test_create_validation_preserves_values(
        client, make_user, login_as, payload, field):
    login_as(client, make_user())
    response = client.post('/complaints/new', data=payload)
    assert response.status_code == 200
    assert field.encode() in response.data
    assert db.session.scalar(db.select(db.func.count(Complaint.id))) == 0


def test_detail_permissions_and_overdue_badge(
        client, make_user, make_complaint, login_as):
    owner = make_user(name='Owner')
    stranger = make_user(name='Stranger')
    complaint = make_complaint(owner, created_at=utcnow() - timedelta(hours=60))
    login_as(client, stranger)
    assert client.get(f'/complaints/{complaint.id}').status_code == 403
    login_as(client, owner)
    response = client.get(f'/complaints/{complaint.id}')
    assert response.status_code == 200
    assert b'Overdue' in response.data


def test_missing_detail_returns_404(client, make_user, login_as):
    login_as(client, make_user())
    assert client.get('/complaints/999').status_code == 404


def test_owner_can_edit_pending_and_fields_update(
        client, make_user, make_complaint, login_as):
    owner = make_user()
    complaint = make_complaint(owner)
    login_as(client, owner)
    response = client.post(f'/complaints/{complaint.id}/edit', data={
        'title': 'Updated', 'description': 'New details', 'category': 'Wi-Fi',
        'priority': 'High',
    })
    assert response.status_code == 302
    db.session.refresh(complaint)
    assert (complaint.title, complaint.description, complaint.category,
            complaint.priority) == ('Updated', 'New details', 'Wi-Fi', 'High')


@pytest.mark.parametrize('status', ['In Progress', 'Resolved'])
def test_owner_cannot_edit_non_pending(
        client, make_user, make_complaint, login_as, status):
    owner = make_user()
    complaint = make_complaint(owner, status=status)
    login_as(client, owner)
    assert client.get(f'/complaints/{complaint.id}/edit').status_code == 403


@pytest.mark.parametrize('role', ['student', 'staff', 'admin'])
def test_non_owner_or_non_student_cannot_edit(
    client, make_user, make_complaint, login_as, role
):
    owner = make_user(name='Owner')
    actor = make_user(role=role, name='Actor')
    complaint = make_complaint(owner)
    login_as(client, actor)
    assert client.get(f'/complaints/{complaint.id}/edit').status_code == 403


def test_owner_delete_and_delete_permission_rules(
        client, make_user, make_complaint, login_as):
    owner = make_user(name='Owner')
    other = make_user(name='Other')
    pending = make_complaint(owner)
    login_as(client, other)
    assert client.post(f'/complaints/{pending.id}/delete').status_code == 403
    login_as(client, owner)
    assert client.post(f'/complaints/{pending.id}/delete').status_code == 302
    assert db.session.get(Complaint, pending.id) is None
    in_progress = make_complaint(owner, status='In Progress')
    assert client.post(f'/complaints/{in_progress.id}/delete').status_code == 403


def test_staff_cannot_delete_admin_can_delete_any_and_missing_404(
        client, make_user, make_complaint, login_as):
    owner = make_user(name='Owner')
    complaint = make_complaint(owner, status='Resolved')
    staff = make_user(role='staff', name='Staff')
    login_as(client, staff)
    assert client.post(f'/complaints/{complaint.id}/delete').status_code == 403
    admin = make_user(role='admin', name='Admin')
    login_as(client, admin)
    assert client.post(f'/complaints/{complaint.id}/delete').status_code == 302
    assert db.session.get(Complaint, complaint.id) is None
    assert client.post('/complaints/999/delete').status_code == 404


@pytest.mark.parametrize('role', ['staff', 'admin'])
def test_managers_assign_and_unassign(
        client, make_user, make_complaint, login_as, role):
    manager = make_user(role=role, name=f'Manager {role}')
    assignee = make_user(role='staff', name='Assignee')
    complaint = make_complaint()
    login_as(client, manager)
    response = client.post(f'/complaints/{complaint.id}/assign',
                           data={'assigned_to': str(assignee.id)})
    assert response.status_code == 302
    db.session.refresh(complaint)
    assert complaint.assigned_to == assignee.id
    assert client.post(f'/complaints/{complaint.id}/assign',
                       data={'assigned_to': ''}).status_code == 302
    db.session.refresh(complaint)
    assert complaint.assigned_to is None


@pytest.mark.parametrize('bad_id', ['abc', '9999'])
def test_invalid_assignment_is_rejected(client, make_user, make_complaint,
                                        login_as, bad_id):
    login_as(client, make_user(role='staff', name='Staff'))
    complaint = make_complaint()
    assert client.post(f'/complaints/{complaint.id}/assign',
                       data={'assigned_to': bad_id}).status_code == 400


def test_student_cannot_be_assignee_or_assign_complaints(
        client, make_user, make_complaint, login_as):
    student = make_user(name='Student')
    complaint = make_complaint()
    login_as(client, make_user(role='staff', name='Manager'))
    assert client.post(f'/complaints/{complaint.id}/assign',
                       data={'assigned_to': str(student.id)}).status_code == 400
    login_as(client, student)
    assert client.post(f'/complaints/{complaint.id}/assign',
                       data={'assigned_to': ''}).status_code == 403


@pytest.mark.parametrize('role', ['staff', 'admin'])
def test_managers_update_status_and_resolved_timestamp(
        client, make_user, make_complaint, login_as, role):
    manager = make_user(role=role, name=f'Manager {role}')
    complaint = make_complaint()
    login_as(client, manager)
    assert client.post(f'/complaints/{complaint.id}/status',
                       data={'status': 'Resolved'}).status_code == 302
    db.session.refresh(complaint)
    assert complaint.status == 'Resolved' and complaint.resolved_at is not None
    for status in ('Pending', 'Resolved', 'In Progress'):
        client.post(f'/complaints/{complaint.id}/status', data={'status': status})
        db.session.refresh(complaint)
        assert complaint.status == status
        assert (complaint.resolved_at is not None) == (status == 'Resolved')


def test_student_cannot_update_status_invalid_rejected_missing_404(
        client, make_user, make_complaint, login_as):
    complaint = make_complaint()
    login_as(client, make_user())
    assert client.post(f'/complaints/{complaint.id}/status',
                       data={'status': 'Resolved'}).status_code == 403
    login_as(client, make_user(role='staff', name='Staff'))
    assert client.post(f'/complaints/{complaint.id}/status',
                       data={'status': 'Broken'}).status_code == 400
    response = client.post(
        '/complaints/999/status', data={'status': 'Pending'})
    assert response.status_code == 404
    response = client.post(
        '/complaints/999/assign', data={'assigned_to': ''})
    assert response.status_code == 404
