"""Pytest fixtures for HostelOps test suite."""
import pytest
from hostelops import create_app
from hostelops.extensions import db


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
