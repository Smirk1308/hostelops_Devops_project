"""Tests for Module 1 authentication and UI shell."""
import pytest
from flask import abort

import scripts.seed as seed_script
from scripts.seed import (
    SeedConfigurationError,
    load_demo_passwords,
    load_seed_environment,
)
from hostelops import create_app
from hostelops.extensions import db
from hostelops.models import User


def register(client, **fields):
    """Submit the registration form with valid defaults and overrides."""
    form = {
        'name': 'A Student',
        'email': 'student@example.com',
        'password': 'longpassword',
        'confirm_password': 'longpassword',
        'room_no': 'B-12',
    }
    form.update(fields)
    return client.post('/register', data=form, follow_redirects=True)


def test_successful_registration(client):
    response = register(client)
    user = User.query.filter_by(email='student@example.com').one()
    assert response.status_code == 200
    assert b'Registration successful' in response.data
    assert user.name == 'A Student'
    assert user.room_no == 'B-12'


@pytest.mark.parametrize('fields,message', [
    ({'name': ''}, b'Name is required'),
    ({'name': '   '}, b'Name is required'),
    ({'email': ''}, b'Email is required'),
    ({'password': ''}, b'Password is required'),
    ({'password': 'short'}, b'at least 8 characters'),
    ({'confirm_password': 'different'}, b'do not match'),
])
def test_registration_required_fields_and_password_rules(client, fields, message):
    response = register(client, **fields)
    assert message in response.data
    assert User.query.count() == 0


@pytest.mark.parametrize('email', [
    'user@', '@example.com', 'user@@example.com', 'user.example.com',
    'user..name@example.com', 'user@example..com',
])
def test_malformed_email_is_rejected(client, email):
    response = register(client, email=email)
    assert b'valid email' in response.data
    assert User.query.count() == 0


def test_duplicate_email_rejected_case_insensitively(client, make_user):
    make_user(email='Student@Example.com')
    response = register(client, email='student@example.com')
    assert b'already exists' in response.data
    assert User.query.count() == 1


def test_registration_trims_and_normalizes_values(client):
    response = register(
        client,
        name='  Alice Example  ',
        email='  Student@Example.com  ',
        room_no='  A-3  ',
    )
    user = User.query.one()
    assert response.status_code == 200
    assert user.name == 'Alice Example'
    assert user.email == 'student@example.com'
    assert user.room_no == 'A-3'


def test_room_number_is_optional_and_empty_becomes_none(client):
    register(client, room_no='   ')
    assert User.query.one().room_no is None


@pytest.mark.parametrize('field,value,message', [
    ('name', 'N' * 101, b'100 characters or fewer'),
    ('email', f"{'a' * 64}@{'b' * 53}.com", b'120 characters or fewer'),
    ('room_no', 'R' * 21, b'20 characters or fewer'),
])
def test_registration_respects_database_field_lengths(
        client, field, value, message):
    response = register(client, **{field: value})
    assert message in response.data
    assert User.query.count() == 0


@pytest.mark.parametrize('role', ['staff', 'admin'])
def test_registration_cannot_assign_privileged_roles(client, role):
    register(client, role=role)
    assert User.query.one().role == 'student'


def test_registration_stores_a_password_hash(client):
    register(client)
    user = User.query.one()
    assert user.password_hash != 'longpassword'
    assert user.check_password('longpassword')


def test_successful_login_establishes_session(client, make_user):
    make_user(email='student@example.com')
    response = client.post('/login', data={
        'email': 'student@example.com', 'password': 'password123',
    })
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/complaints')
    with client.session_transaction() as session:
        assert session['_user_id']


def test_login_normalizes_email_case(client, make_user):
    make_user(email='Student@Example.com')
    response = client.post('/login', data={
        'email': '  STUDENT@example.com ', 'password': 'password123',
    })
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/complaints')


@pytest.mark.parametrize('email,password', [
    ('student@example.com', 'wrongpassword'),
    ('missing@example.com', 'password123'),
])
def test_invalid_login_uses_generic_message(client, make_user, email, password):
    make_user(email='student@example.com')
    response = client.post('/login', data={
        'email': email, 'password': password,
    })
    assert response.status_code == 401
    assert b'Invalid email or password.' in response.data


def test_authenticated_user_visiting_login_is_redirected(
        client, make_user, login_as):
    user = make_user(email='student@example.com')
    login_as(client, user)
    response = client.get('/login')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/complaints')


def test_safe_internal_next_url_is_accepted(client, make_user):
    make_user(email='student@example.com')
    response = client.post('/login?next=/complaints/42', data={
        'email': 'student@example.com', 'password': 'password123',
    })
    assert response.headers['Location'].endswith('/complaints/42')


@pytest.mark.parametrize('next_url', [
    'https://example.com', '//example.com/path', '/\\example.com',
])
def test_external_next_urls_are_rejected(client, make_user, next_url):
    make_user(email='student@example.com')
    response = client.post('/login', query_string={'next': next_url}, data={
        'email': 'student@example.com', 'password': 'password123',
    })
    assert response.headers['Location'].endswith('/complaints')
    assert 'example.com' not in response.headers['Location']


def test_authenticated_post_logout_clears_session(client, make_user, login_as):
    user = make_user(email='student@example.com')
    login_as(client, user)
    response = client.post('/logout')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_unauthenticated_post_logout_cannot_log_user_out(client):
    response = client.post('/logout')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
    assert b'logged out' not in response.data
    with client.session_transaction() as session:
        assert '_user_id' not in session


def test_logout_is_not_available_as_get(client):
    assert client.get('/logout').status_code == 405


def test_auth_pages_render_with_csrf_fields(client):
    for path in ('/login', '/register'):
        response = client.get(path)
        assert response.status_code == 200
        assert b'name="csrf-token"' in response.data
        assert b'name="csrf_token"' in response.data


@pytest.mark.parametrize('role', ['student', 'staff', 'admin'])
def test_navigation_matches_authenticated_role(client, make_user, login_as, role):
    user = make_user(role=role)
    login_as(client, user)
    response = client.get('/not-a-real-route')
    assert response.status_code == 404
    assert b'/complaints' in response.data
    assert b'Log out' in response.data
    assert b'/admin/users' not in response.data
    if role == 'student':
        assert b'/complaints/new' in response.data
        assert b'/dashboard' not in response.data
    else:
        assert b'/dashboard' in response.data
        assert b'/complaints/new' not in response.data


def test_anonymous_navigation_shows_auth_links(client):
    response = client.get('/login')
    assert b'href="/login"' in response.data
    assert b'href="/register"' in response.data
    assert b'Log out' not in response.data


def test_friendly_403_page_has_correct_status(app, client):
    app.add_url_rule(
        '/_test/forbidden', 'test_forbidden', lambda: abort(403)
    )
    response = client.get('/_test/forbidden')
    assert response.status_code == 403
    assert b'Access denied' in response.data
    assert b'/complaints' in response.data


def test_friendly_404_page_has_correct_status(client):
    response = client.get('/not-a-real-route')
    assert response.status_code == 404
    assert b'Page not found' in response.data
    assert b'/complaints' in response.data


def test_normal_application_keeps_csrf_protection_enabled():
    app = create_app(test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'csrf-test-secret',
    })
    assert app.config.get('WTF_CSRF_ENABLED', True) is True
    response = app.test_client().post('/register', data={'name': 'No token'})
    assert response.status_code == 400


def test_seed_requires_explicit_opt_in():
    environment = {
        'HOSTELOPS_SEED_ADMIN_PASSWORD': 'AdminDemoSecret!29',
        'HOSTELOPS_SEED_STAFF_PASSWORD': 'StaffDemoSecret!38',
        'HOSTELOPS_SEED_STUDENT_PASSWORD': 'StudentDemoSecret!47',
    }
    with pytest.raises(
            SeedConfigurationError, match='HOSTELOPS_ENABLE_DEMO_SEED'):
        load_demo_passwords(environment)


def test_seed_reports_missing_password_variables():
    with pytest.raises(SeedConfigurationError, match='HOSTELOPS_SEED_ADMIN_PASSWORD'):
        load_demo_passwords({'HOSTELOPS_ENABLE_DEMO_SEED': '1'})


def test_seed_rejects_weak_configured_password():
    environment = {
        'HOSTELOPS_ENABLE_DEMO_SEED': '1',
        'HOSTELOPS_SEED_ADMIN_PASSWORD': 'short',
        'HOSTELOPS_SEED_STAFF_PASSWORD': 'UnusedStrongStaff!9',
        'HOSTELOPS_SEED_STUDENT_PASSWORD': 'UnusedStrongStudent!9',
    }
    with pytest.raises(SeedConfigurationError, match='at least 12 characters'):
        load_demo_passwords(environment)


def test_seed_accepts_strong_passwords():
    environment = {
        'HOSTELOPS_ENABLE_DEMO_SEED': '1',
        'HOSTELOPS_SEED_ADMIN_PASSWORD': 'AdminDemoSecret!29',
        'HOSTELOPS_SEED_STAFF_PASSWORD': 'StaffDemoSecret!38',
        'HOSTELOPS_SEED_STUDENT_PASSWORD': 'StudentDemoSecret!47',
    }
    passwords = load_demo_passwords(environment)
    assert set(passwords) == {'admin', 'staff', 'student'}
    assert passwords == {
        'admin': environment['HOSTELOPS_SEED_ADMIN_PASSWORD'],
        'staff': environment['HOSTELOPS_SEED_STAFF_PASSWORD'],
        'student': environment['HOSTELOPS_SEED_STUDENT_PASSWORD'],
    }


def _seed_environment(**overrides):
    environment = {
        'HOSTELOPS_ENABLE_DEMO_SEED': '1',
        'HOSTELOPS_SEED_ADMIN_PASSWORD': 'AdminDemoSecret!29',
        'HOSTELOPS_SEED_STAFF_PASSWORD': 'StaffDemoSecret!38',
        'HOSTELOPS_SEED_STUDENT_PASSWORD': 'StudentDemoSecret!47',
    }
    environment.update(overrides)
    return environment


def test_seed_loads_dotenv_from_repository_root_and_shell_wins(
        tmp_path, monkeypatch):
    dotenv_file = tmp_path / '.env'
    dotenv_file.write_text(
        'HOSTELOPS_ENABLE_DEMO_SEED=1\n'
        'HOSTELOPS_SEED_ADMIN_PASSWORD=FromDotEnvSecret!29\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(seed_script, 'ROOT_DIR', tmp_path)
    monkeypatch.delenv('HOSTELOPS_ENABLE_DEMO_SEED', raising=False)
    monkeypatch.delenv('HOSTELOPS_SEED_ADMIN_PASSWORD', raising=False)
    monkeypatch.setenv('HOSTELOPS_SEED_STAFF_PASSWORD', 'ShellStaffSecret!38')
    environment = load_seed_environment()
    assert environment['HOSTELOPS_ENABLE_DEMO_SEED'] == '1'
    assert environment['HOSTELOPS_SEED_ADMIN_PASSWORD'] == 'FromDotEnvSecret!29'
    assert environment['HOSTELOPS_SEED_STAFF_PASSWORD'] == 'ShellStaffSecret!38'


def test_injected_seed_environment_skips_dotenv_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(seed_script, 'ROOT_DIR', tmp_path)
    (tmp_path / '.env').write_text('UNEXPECTED=value', encoding='utf-8')
    injected = {'HOSTELOPS_ENABLE_DEMO_SEED': '1'}
    assert load_seed_environment(injected) is injected


@pytest.mark.parametrize('production_marker', [
    {'ENVIRONMENT': 'production'},
    {'FLASK_ENV': 'Production'},
    {'HOSTELOPS_ENV': 'prod'},
    {'APP_ENV': 'production'},
    {'RENDER': 'true'},
])
def test_seed_rejects_production_environment(production_marker):
    with pytest.raises(SeedConfigurationError, match='disabled in production'):
        load_demo_passwords(_seed_environment(**production_marker))


def test_seed_does_not_print_password_values(app, monkeypatch, capsys):
    monkeypatch.setattr(seed_script, 'create_app', lambda: app)
    environment = _seed_environment()
    seed_script.seed(environment)
    output = capsys.readouterr().out
    for variable in (
            'HOSTELOPS_SEED_ADMIN_PASSWORD',
            'HOSTELOPS_SEED_STAFF_PASSWORD',
            'HOSTELOPS_SEED_STUDENT_PASSWORD'):
        assert environment[variable] not in output


def test_seed_creates_demo_accounts_and_is_idempotent(app, monkeypatch, capsys):
    monkeypatch.setattr(seed_script, 'create_app', lambda: app)
    environment = _seed_environment()
    seed_script.seed(environment)
    assert User.query.count() == 3
    assert User.query.filter_by(email='admin@hostelops.local').one().check_password(
        environment['HOSTELOPS_SEED_ADMIN_PASSWORD'])
    assert '15 complaint(s) created' in capsys.readouterr().out

    seed_script.seed(environment)
    assert User.query.count() == 3
    assert '0 complaint(s) created' in capsys.readouterr().out


def test_seed_preserves_existing_passwords_until_explicit_rotation(
        app, monkeypatch, make_user, capsys):
    monkeypatch.setattr(seed_script, 'create_app', lambda: app)
    demo_accounts = [
        ('admin', 'admin@hostelops.local'),
        ('staff', 'staff@hostelops.local'),
        ('student', 'student@hostelops.local'),
    ]
    accounts = {}
    for role, email in demo_accounts:
        accounts[email] = make_user(
            role=role, email=email, password='OldDemoPassword!29',
            name=f'Preserved {role}', room_no='Keep-This',
        )
    ordinary = make_user(email='ordinary@example.com', password='Ordinary!Password29')
    environment = _seed_environment()

    seed_script.seed(environment)
    for email, account in accounts.items():
        assert account.check_password('OldDemoPassword!29')
        assert account.name.startswith('Preserved ')
        assert account.room_no == 'Keep-This'
    assert ordinary.check_password('Ordinary!Password29')
    capsys.readouterr()

    rotated = _seed_environment(HOSTELOPS_ROTATE_DEMO_PASSWORDS='1')
    seed_script.seed(rotated)
    db.session.expire_all()
    for role, email in demo_accounts:
        account = User.query.filter_by(email=email).one()
        assert account.check_password(rotated[
            f'HOSTELOPS_SEED_{role.upper()}_PASSWORD'
        ])
        assert account.role == role
        assert account.name.startswith('Preserved ')
        assert account.room_no == 'Keep-This'
    assert ordinary.check_password('Ordinary!Password29')
    assert User.query.count() == 4
    assert '15 complaint(s) created' in capsys.readouterr().out


def test_seed_rejects_missing_configuration_without_fallbacks():
    with pytest.raises(SeedConfigurationError, match='Missing required') as error:
        load_demo_passwords({'HOSTELOPS_ENABLE_DEMO_SEED': '1'})
    assert 'admin123' not in str(error.value)
