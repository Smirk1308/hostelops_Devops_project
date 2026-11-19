"""Tests for Module 1 authentication and UI shell."""
import pytest
from flask import g

from hostelops.extensions import db
from hostelops.models import User


@pytest.fixture
def make_user(app):
    """Return a helper that creates users with convenient defaults."""
    def create_user(role='student', email='student@example.com',
                    password='password123', name='Test Student', room_no='101'):
        user = User(name=name, email=email, role=role, room_no=room_no)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return create_user


@pytest.fixture
def login_as(app, client):
    """Log a user into the test client through Flask-Login's session keys."""
    def authenticate(user):
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True
        with app.test_request_context():
            g.pop('_login_user', None)

    return authenticate


def register(client, **fields):
    """Submit the standard registration form with optional overrides."""
    form = {
        'name': 'A Student',
        'email': 'student@example.com',
        'password': 'longpassword',
        'confirm_password': 'longpassword',
        'room_no': 'B-12',
    }
    form.update(fields)
    return client.post('/register', data=form, follow_redirects=True)


def test_successful_registration(client, app):
    response = register(client)
    user = User.query.filter_by(email='student@example.com').one()
    assert response.status_code == 200
    assert b'Registration successful' in response.data
    assert user.name == 'A Student'
    assert user.room_no == 'B-12'


def test_duplicate_email_rejected(client, make_user):
    make_user()
    response = register(client)
    assert b'already exists' in response.data
    assert User.query.count() == 1


def test_missing_email_rejected(client):
    response = register(client, email='')
    assert b'Email is required' in response.data


def test_invalid_email_rejected(client):
    response = register(client, email='not-an-email')
    assert b'valid email' in response.data


def test_short_password_rejected(client):
    response = register(client, password='short', confirm_password='short')
    assert b'at least 8 characters' in response.data


def test_password_confirmation_mismatch_rejected(client):
    response = register(client, confirm_password='somethingelse')
    assert b'do not match' in response.data


def test_registration_always_assigns_student_role(client):
    client.post('/register', data={
        'name': 'A Student', 'email': 'student@example.com',
        'password': 'longpassword', 'confirm_password': 'longpassword',
        'role': 'admin',
    })
    assert User.query.one().role == 'student'


def test_registration_stores_hashed_password(client):
    register(client)
    user = User.query.one()
    assert user.password_hash != 'longpassword'
    assert user.check_password('longpassword')


def test_successful_login(client, make_user):
    make_user()
    response = client.post('/login', data={
        'email': 'student@example.com', 'password': 'password123',
    })
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/complaints')


@pytest.mark.parametrize('email,password', [
    ('student@example.com', 'wrongpassword'),
    ('missing@example.com', 'password123'),
])
def test_invalid_login_shows_generic_message(client, make_user, email, password):
    make_user()
    response = client.post('/login', data={
        'email': email, 'password': password,
    })
    assert response.status_code == 401
    assert b'Invalid email or password.' in response.data


def test_logout_works(client, make_user, login_as):
    login_as(make_user())
    response = client.post('/logout')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')
    with client:
        response = client.get('/login')
        assert response.status_code == 200


def test_logout_is_not_available_as_get(client):
    assert client.get('/logout').status_code == 405


def test_authenticated_user_visiting_login_is_redirected(
        client, make_user, login_as):
    login_as(make_user())
    response = client.get('/login')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/complaints')


def test_safe_internal_next_url_is_accepted(client, make_user):
    make_user()
    response = client.post('/login?next=/complaints/42', data={
        'email': 'student@example.com', 'password': 'password123',
    })
    assert response.headers['Location'].endswith('/complaints/42')


@pytest.mark.parametrize('next_url', [
    'https://example.com', '//example.com/path', '/\\example.com',
])
def test_external_next_url_is_rejected(client, make_user, next_url):
    make_user()
    response = client.post('/login', query_string={'next': next_url}, data={
        'email': 'student@example.com', 'password': 'password123',
    })
    assert response.headers['Location'].endswith('/complaints')
    assert 'example.com' not in response.headers['Location']
