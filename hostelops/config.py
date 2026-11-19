"""HostelOps configuration settings."""
import os

INSECURE_SECRET_KEYS = {
    'dev',
    'dev-secret-key-change-in-production',
    'test-secret-key',
    'secret',
    'password',
    'change-me',
    'default',
}


def normalize_database_url(url=None):
    """Normalize database connection URLs for SQLAlchemy compatibility.

    Converts legacy 'postgres://' (standard on Render) and 'postgresql://' to
    'postgresql+psycopg2://' so SQLAlchemy selects the installed psycopg2 driver
    instead of defaulting to psycopg 3. Preserves SQLite URIs and falls back to
    local SQLite if empty.
    """
    if not url or not str(url).strip():
        return 'sqlite:///hostelops.db'
    url = str(url).strip()
    if url.startswith('postgresql+psycopg2://'):
        return url
    if url.startswith('postgres://'):
        return 'postgresql+psycopg2://' + url[len('postgres://'):]
    if url.startswith('postgresql://'):
        return 'postgresql+psycopg2://' + url[len('postgresql://'):]
    return url


def is_production(environ=None):
    """Detect if running in an explicit production or Render environment."""
    env = os.environ if environ is None else environ
    prod_values = {'production', 'prod'}
    markers = ('HOSTELOPS_ENV', 'FLASK_ENV', 'ENVIRONMENT', 'APP_ENV')
    if any(str(env.get(k, '')).strip().lower() in prod_values for k in markers):
        return True
    if str(env.get('RENDER', '')).strip().lower() in ('true', '1', 'yes'):
        return True
    return False


def validate_production_config(config, environ=None):
    """Validate that production configuration meets strict security standards.

    Raises RuntimeError if SECRET_KEY is missing, too short, or uses a known
    insecure value. Never exposes the candidate secret key value in logs or errors.
    """
    env = os.environ if environ is None else environ
    secret_key = config.get('SECRET_KEY')
    if secret_key is None:
        secret_key = env.get('SECRET_KEY', '')

    if not secret_key or not str(secret_key).strip():
        raise RuntimeError(
            'Missing SECRET_KEY in production. '
            'A strong SECRET_KEY must be explicitly configured.'
        )

    if str(secret_key).strip().lower() in INSECURE_SECRET_KEYS:
        raise RuntimeError(
            'Insecure development SECRET_KEY detected in production. '
            'Configure a strong, unique SECRET_KEY.'
        )

    if len(str(secret_key)) < 16:
        raise RuntimeError(
            'SECRET_KEY in production is too weak (must be at least 16 characters).'
        )


class Config:
    """Base application configuration with environment variable support."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = normalize_database_url(
        os.environ.get('DATABASE_URL')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    try:
        OVERDUE_HOURS = int(os.environ.get('OVERDUE_HOURS', 48))
    except (TypeError, ValueError):
        OVERDUE_HOURS = 48
    MODEL_PATH = os.environ.get('MODEL_PATH', 'ml/model.joblib')
    APP_VERSION = os.environ.get('APP_VERSION', '0.1.0')


class TestConfig(Config):
    """Configuration used during automated testing."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
