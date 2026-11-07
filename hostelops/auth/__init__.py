"""Authentication and user management blueprint (Module 1)."""
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from hostelops.auth import routes  # noqa: F401, E402

__all__ = ['auth_bp']
