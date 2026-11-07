"""HostelOps application package and factory."""
import os
from flask import Flask
from jinja2 import ChoiceLoader, FileSystemLoader

from hostelops.auth import auth_bp
from hostelops.complaints import complaints_bp
from hostelops.config import Config
from hostelops.extensions import csrf, db, login_manager
from hostelops.models import Complaint, User
from hostelops.triage import triage_bp


def create_app(config_object=None, test_config=None):
    """Create and configure the HostelOps Flask application instance."""
    package_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.dirname(package_dir)

    app = Flask(
        __name__,
        template_folder=os.path.join(package_dir, 'templates'),
        static_folder=os.path.join(package_dir, 'static'),
    )

    # Allow Jinja to find templates in root templates/ as well as hostelops/templates
    loaders = [app.jinja_loader]
    root_templates = os.path.join(project_root, 'templates')
    pkg_templates = os.path.join(package_dir, 'templates')
    if os.path.isdir(root_templates):
        loaders.append(FileSystemLoader(root_templates))
    if os.path.isdir(pkg_templates):
        loaders.append(FileSystemLoader(pkg_templates))
    app.jinja_loader = ChoiceLoader(loaders)

    # Load configuration
    app.config.from_object(Config)
    if config_object:
        app.config.from_object(config_object)
    if test_config:
        app.config.update(test_config)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(triage_bp)

    # Health check route
    @app.route('/health')
    def health():
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
