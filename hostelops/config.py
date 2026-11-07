"""HostelOps configuration settings."""
import os


class Config:
    """Base application configuration with environment variable support."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'sqlite:///hostelops.db'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OVERDUE_HOURS = int(os.environ.get('OVERDUE_HOURS', 48))
    MODEL_PATH = os.environ.get('MODEL_PATH', 'ml/model.joblib')
    APP_VERSION = os.environ.get('APP_VERSION', '0.1.0')


class TestConfig(Config):
    """Configuration used during automated testing."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
