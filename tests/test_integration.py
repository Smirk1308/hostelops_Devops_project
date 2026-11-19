"""End-to-end integration tests for HostelOps."""
import re
from datetime import timedelta

import pytest

from hostelops import create_app
from hostelops.config import normalize_database_url, validate_production_config
from hostelops.extensions import db
from hostelops.models import CATEGORIES, PRIORITIES, Complaint, utcnow


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


# ===========================================================================
# 1. CSRF Protection Integration Tests
# ===========================================================================

def test_default_app_has_csrf_protection_enabled():
    """Verify standard application factory enables CSRF protection."""
    app = create_app()
    assert app.config.get('WTF_CSRF_ENABLED', True) is True


def test_csrf_valid_token_allows_authenticated_post(
    csrf_app, csrf_client, make_csrf_user
):
    """Verify that a valid CSRF token permits authentication."""
    make_csrf_user(
        role='student', email='csrf_student@test.local', password='password123'
    )
    r_page = csrf_client.get('/login')
    token = _extract_csrf(r_page.text)
    assert token != ''

    r_login = csrf_client.post('/login', data={
        'csrf_token': token,
        'email': 'csrf_student@test.local',
        'password': 'password123',
    }, follow_redirects=True)
    assert r_login.status_code == 200
    assert b'Complaints' in r_login.data


def test_csrf_missing_token_is_rejected(csrf_app, csrf_client, make_csrf_user):
    """Verify that POST without CSRF token is rejected with 400 Bad Request."""
    make_csrf_user(
        role='student', email='csrf_no_token@test.local', password='password123'
    )
    r = csrf_client.post('/login', data={
        'email': 'csrf_no_token@test.local',
        'password': 'password123',
    })
    assert r.status_code == 400


def test_csrf_invalid_token_is_rejected(csrf_app, csrf_client, make_csrf_user):
    """Verify that POST with invalid CSRF token is rejected with 400 Bad Request."""
    make_csrf_user(
        role='student', email='csrf_bad_token@test.local', password='password123'
    )
    r = csrf_client.post('/login', data={
        'csrf_token': 'tampered-csrf-token-xyz',
        'email': 'csrf_bad_token@test.local',
        'password': 'password123',
    })
    assert r.status_code == 400


def test_csrf_complaint_and_logout_flow(csrf_app, csrf_client, make_csrf_user):
    """Verify that complaint creation and logout succeed with valid CSRF tokens."""
    student = make_csrf_user(
        role='student', email='csrf_flow@test.local', password='password123'
    )

    # 1. Login with CSRF
    r_login_page = csrf_client.get('/login')
    token = _extract_csrf(r_login_page.text)
    csrf_client.post('/login', data={
        'csrf_token': token,
        'email': 'csrf_flow@test.local',
        'password': 'password123',
    }, follow_redirects=True)

    # 2. Submit complaint with CSRF
    r_form = csrf_client.get('/complaints/new')
    form_token = _extract_csrf(r_form.text)
    r_create = csrf_client.post('/complaints/new', data={
        'csrf_token': form_token,
        'title': 'Broken desk leg',
        'description': 'The left front leg of the study table is cracked.',
        'category': 'Furniture',
        'priority': 'Low',
    }, follow_redirects=True)
    assert r_create.status_code == 200
    assert b'submitted' in r_create.data

    with csrf_app.app_context():
        c = db.session.scalar(
            db.select(Complaint).where(Complaint.created_by == student.id)
        )
        assert c is not None
        assert c.title == 'Broken desk leg'

    # 3. Logout with CSRF
    logout_token = _extract_csrf(r_create.text)
    r_logout = csrf_client.post(
        '/logout', data={'csrf_token': logout_token}, follow_redirects=True
    )
    assert r_logout.status_code == 200
    assert b'logged out' in r_logout.data


# ===========================================================================
# 2. Machine Learning Triage Integration Tests
# ===========================================================================

def test_ml_triage_integration_with_model(
    csrf_app, csrf_client, make_csrf_user, model_file
):
    """Test that ML suggest API returns non-null predictions with trained model."""
    csrf_app.config['MODEL_PATH'] = str(model_file)
    from hostelops.triage import predictor
    predictor.clear_cache()

    make_csrf_user(
        role='student', email='ml_user@test.local', password='password123'
    )
    r_login = csrf_client.get('/login')
    token = _extract_csrf(r_login.text)
    csrf_client.post('/login', data={
        'csrf_token': token,
        'email': 'ml_user@test.local',
        'password': 'password123',
    }, follow_redirects=True)

    r_suggest = csrf_client.post(
        '/api/triage/suggest',
        json={'text': 'No water supply in Block A washroom since morning'},
        headers={'X-CSRFToken': token},
    )
    assert r_suggest.status_code == 200
    data = r_suggest.get_json()

    assert data['category'] is not None
    assert data['category'] in CATEGORIES
    assert data['category'] == 'Water'

    assert data['priority'] is not None
    assert data['priority'] in PRIORITIES

    assert isinstance(data['confidence'], float)
    assert 0.0 < data['confidence'] <= 1.0


def test_ml_triage_missing_model_fallback(
    csrf_app, csrf_client, make_csrf_user, tmp_path
):
    """Verify graceful (None, None, 0.0) fallback when model file is missing."""
    csrf_app.config['MODEL_PATH'] = str(tmp_path / 'missing_model.joblib')
    from hostelops.triage import predictor
    predictor.clear_cache()

    make_csrf_user(
        role='student', email='fallback_user@test.local', password='password123'
    )
    r_login = csrf_client.get('/login')
    token = _extract_csrf(r_login.text)
    csrf_client.post('/login', data={
        'csrf_token': token,
        'email': 'fallback_user@test.local',
        'password': 'password123',
    }, follow_redirects=True)

    r = csrf_client.post(
        '/api/triage/suggest',
        json={'text': 'Sparks from electrical switchboard'},
        headers={'X-CSRFToken': token},
    )
    assert r.status_code == 200
    data = r.get_json()
    assert data['category'] is None
    assert data['priority'] is None
    assert data['confidence'] == 0.0


def test_ml_triage_short_and_malformed_inputs(
    csrf_app, csrf_client, make_csrf_user, model_file
):
    """Verify safe handling of short, blank, and malformed inputs."""
    csrf_app.config['MODEL_PATH'] = str(model_file)
    from hostelops.triage import predictor
    predictor.clear_cache()

    make_csrf_user(
        role='student', email='inputs_user@test.local', password='password123'
    )
    r_login = csrf_client.get('/login')
    token = _extract_csrf(r_login.text)
    csrf_client.post('/login', data={
        'csrf_token': token,
        'email': 'inputs_user@test.local',
        'password': 'password123',
    }, follow_redirects=True)

    # 1. Text shorter than 5 characters returns nulls and 0.0
    r_short = csrf_client.post(
        '/api/triage/suggest',
        json={'text': 'leak'},
        headers={'X-CSRFToken': token},
    )
    assert r_short.status_code == 200
    assert r_short.get_json() == {
        'category': None, 'priority': None, 'confidence': 0.0
    }

    # 2. Blank whitespace text returns nulls and 0.0
    r_blank = csrf_client.post(
        '/api/triage/suggest',
        json={'text': '    '},
        headers={'X-CSRFToken': token},
    )
    assert r_blank.status_code == 200
    assert r_blank.get_json() == {
        'category': None, 'priority': None, 'confidence': 0.0
    }

    # 3. Malformed JSON (missing 'text' key) returns 400
    r_missing_key = csrf_client.post(
        '/api/triage/suggest',
        json={'other_key': 'description text'},
        headers={'X-CSRFToken': token},
    )
    assert r_missing_key.status_code == 400

    # 4. Non-string 'text' key returns 400
    r_non_string = csrf_client.post(
        '/api/triage/suggest',
        json={'text': 12345},
        headers={'X-CSRFToken': token},
    )
    assert r_non_string.status_code == 400


# ===========================================================================
# 3. Production Security Validation Tests
# ===========================================================================

def test_production_startup_rejects_missing_or_insecure_secrets():
    """Verify that production startup rejects missing, weak, or default keys."""
    # 1. Missing secret key
    with pytest.raises(RuntimeError, match='Missing SECRET_KEY in production'):
        validate_production_config({'SECRET_KEY': ''})

    # 2. Insecure development default keys
    for insecure in ('dev', 'dev-secret-key-change-in-production', 'test-secret-key'):
        with pytest.raises(RuntimeError, match='Insecure development SECRET_KEY'):
            validate_production_config({'SECRET_KEY': insecure})

    # 3. Short secret key (< 16 characters)
    with pytest.raises(RuntimeError, match='too weak'):
        validate_production_config({'SECRET_KEY': 'too-short-key'})


def test_production_startup_accepts_valid_secret(monkeypatch):
    """Verify that production startup succeeds with strong secret and sets cookies."""
    monkeypatch.setenv('RENDER', 'true')
    monkeypatch.setenv('SECRET_KEY', 'SuperSecretProdKey_at_least_16_chars_123!')

    prod_app = create_app()
    assert prod_app.config['SESSION_COOKIE_SECURE'] is True
    assert prod_app.config['SESSION_COOKIE_HTTPONLY'] is True
    assert prod_app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'
    assert prod_app.config['DEBUG'] is False


def test_development_allows_default_secret_key(monkeypatch):
    """Verify that local development works with default dev settings."""
    monkeypatch.delenv('RENDER', raising=False)
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    monkeypatch.delenv('FLASK_ENV', raising=False)
    monkeypatch.delenv('HOSTELOPS_ENV', raising=False)
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.setenv('SECRET_KEY', 'dev')

    dev_app = create_app()
    assert dev_app.config['SECRET_KEY'] == 'dev'


# ===========================================================================
# 4. PostgreSQL and Database URI Normalization Tests
# ===========================================================================

def test_database_url_normalization():
    """Verify PostgreSQL URL normalization and SQLite fallback defaults."""
    # Render legacy postgres:// scheme
    assert normalize_database_url(
        'postgres://user:pass@ep-sample.render.com:5432/hostelops'
    ) == 'postgresql://user:pass@ep-sample.render.com:5432/hostelops'

    # Standard postgresql:// scheme
    assert normalize_database_url(
        'postgresql://user:pass@localhost:5432/hostelops'
    ) == 'postgresql://user:pass@localhost:5432/hostelops'

    # Local SQLite default and custom paths
    assert normalize_database_url('sqlite:///hostelops.db') == 'sqlite:///hostelops.db'
    assert normalize_database_url('sqlite:////var/data/hostel.db') == (
        'sqlite:////var/data/hostel.db'
    )
    assert normalize_database_url(None) == 'sqlite:///hostelops.db'
    assert normalize_database_url('') == 'sqlite:///hostelops.db'
    assert normalize_database_url('   ') == 'sqlite:///hostelops.db'


# ===========================================================================
# 5. Full Lifecycle & Overdue Integration Tests
# ===========================================================================

def test_complete_complaint_lifecycle_and_analytics(app, client, make_user):
    """Test full workflow: student reports, staff manages, analytics updates."""
    student = make_user(
        role='student', email='alice@test.local', password='password123',
        name='Alice Smith', room_no='A-101'
    )
    staff = make_user(
        role='staff', email='bob@test.local', password='password123',
        name='Bob Staff'
    )

    r_login_page = client.get('/login')
    csrf_token = _extract_csrf(r_login_page.text)
    r_login = client.post('/login', data={
        'csrf_token': csrf_token,
        'email': 'alice@test.local',
        'password': 'password123',
    }, follow_redirects=True)
    assert r_login.status_code == 200
    assert b'Complaints' in r_login.data

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

    complaint = db.session.scalar(
        db.select(Complaint).where(Complaint.created_by == student.id)
    )
    assert complaint is not None
    assert complaint.status == 'Pending'
    assert complaint.assigned_to is None
    assert complaint.resolved_at is None

    # Student cannot access staff dashboard
    assert client.get('/dashboard').status_code == 403
    assert client.get('/api/stats').status_code == 403

    # Student logs out
    csrf_logout = _extract_csrf(r_create.text)
    r_logout = client.post(
        '/logout', data={'csrf_token': csrf_logout}, follow_redirects=True
    )
    assert r_logout.status_code == 200
    assert b'logged out' in r_logout.data

    # Staff logs in
    r_staff_login_page = client.get('/login')
    csrf_staff = _extract_csrf(r_staff_login_page.text)
    r_staff_login = client.post('/login', data={
        'csrf_token': csrf_staff,
        'email': 'bob@test.local',
        'password': 'password123',
    }, follow_redirects=True)
    assert r_staff_login.status_code == 200
    assert b'Dashboard' in r_staff_login.data

    # Staff views complaints with filter
    r_list = client.get('/complaints?status=Pending&category=Water')
    assert r_list.status_code == 200
    assert b'Leaking bathroom tap' in r_list.data

    # Staff assigns complaint
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

    # Staff updates status to In Progress
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

    # Staff resolves complaint
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

    # Staff checks dashboard and stats API
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

    r_login_page = client.get('/login')
    csrf = _extract_csrf(r_login_page.text)
    client.post('/login', data={
        'csrf_token': csrf,
        'email': 'staff2@test.local',
        'password': 'password123',
    }, follow_redirects=True)

    r_stats = client.get('/api/stats')
    assert r_stats.status_code == 200
    assert r_stats.get_json()['overdue'] >= 1

    r_detail = client.get(f'/complaints/{overdue_complaint.id}')
    assert r_detail.status_code == 200
    assert b'Overdue' in r_detail.data
