"""Pytest fixtures for the HostelOps test suite."""
import pytest
from flask import g

from hostelops import create_app
from hostelops.extensions import db
from hostelops.models import User


@pytest.fixture
def app():
    """Create and configure a clean app instance for each test."""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SECRET_KEY': 'test-secret-key',
        'OVERDUE_HOURS': 48,
        'APP_VERSION': '0.1.0',
    }
    app = create_app(test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client for HTTP requests."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Test runner for CLI commands."""
    return app.test_cli_runner()


@pytest.fixture
def make_user(app):
    """Factory fixture that creates and saves a user."""
    counter = {'n': 0}

    def _make_user(
        role='student',
        email=None,
        password='password123',
        name=None,
        room_no=None,
    ):
        counter['n'] += 1
        number = counter['n']
        user = User(
            name=name or f'Test {role} {number}',
            email=email or f'{role}{number}@test.local',
            role=role,
            room_no=room_no,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


@pytest.fixture
def login_as():
    """Log a test client in without submitting the login form."""

    def _login_as(client, user):
        with client.session_transaction() as session:
            session['_user_id'] = str(user.id)
            session['_fresh'] = True

        # Clear Flask-Login's cached user when switching accounts in a test.
        g.pop('_login_user', None)

    return _login_as


@pytest.fixture(scope='session')
def model_file(tmp_path_factory):
    """Train the triage model once per test session and return the file path."""
    import ml.train as ml_train
    out = tmp_path_factory.mktemp('ml') / 'model.joblib'
    ml_train.train(model_path=out)
    return out


@pytest.fixture
def csrf_app():
    """Create an app instance with CSRF protection explicitly enabled."""
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': True,
        'SECRET_KEY': 'test-csrf-secret-key-for-testing',
        'OVERDUE_HOURS': 48,
        'APP_VERSION': '0.1.0',
    }
    app = create_app(test_config=test_config)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def csrf_client(csrf_app):
    """Test client for HTTP requests with CSRF protection enabled."""
    return csrf_app.test_client()


@pytest.fixture
def make_csrf_user(csrf_app):
    """Factory fixture that creates and saves a user for the CSRF app."""
    counter = {'n': 0}

    def _make_user(
        role='student',
        email=None,
        password='password123',
        name=None,
        room_no=None,
    ):
        counter['n'] += 1
        number = counter['n']
        user = User(
            name=name or f'Test {role} {number}',
            email=email or f'csrf_{role}{number}@test.local',
            role=role,
            room_no=room_no,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user
