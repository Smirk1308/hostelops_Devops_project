"""HostelOps application package and factory."""
import os

from flask import Flask

from hostelops.auth import auth_bp
from hostelops.complaints import complaints_bp
from hostelops.config import (
    Config,
    is_production,
    normalize_database_url,
    validate_production_config,
)
from hostelops.extensions import csrf, db, login_manager
from hostelops.models import Complaint, User
from hostelops.triage import triage_bp


def create_app(config_object=None, test_config=None):
    """Create and configure the HostelOps Flask application instance."""
    package_dir = os.path.abspath(os.path.dirname(__file__))

    app = Flask(
        __name__,
        template_folder=os.path.join(package_dir, 'templates'),
        static_folder=os.path.join(package_dir, 'static'),
    )

    app.config.from_object(Config)
    has_test_secret = test_config and 'SECRET_KEY' in test_config
    if 'SECRET_KEY' in os.environ and not has_test_secret:
        app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    has_test_db = test_config and 'SQLALCHEMY_DATABASE_URI' in test_config
    if 'DATABASE_URL' in os.environ and not has_test_db:
        app.config['SQLALCHEMY_DATABASE_URI'] = normalize_database_url(
            os.environ['DATABASE_URL']
        )
    if config_object:
        app.config.from_object(config_object)
    if test_config:
        app.config.update(test_config)

    # Production security validation and hardening
    if is_production() and not app.config.get('TESTING'):
        validate_production_config(app.config)
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
        app.config['DEBUG'] = False

    # SQLite stores its database under Flask's instance directory.
    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """Load a user from the session safely."""
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(triage_bp)

    # The project uses create_all because it has no migration system.
    with app.app_context():
        db.create_all()

    @app.route('/health')
    def health():
        """Return a lightweight health-check response."""
        return {
            'status': 'ok',
            'version': app.config.get('APP_VERSION', '0.1.0'),
        }

    return app


__all__ = [
    'create_app',
    'db',
    'login_manager',
    'csrf',
    'User',
    'Complaint',
]
