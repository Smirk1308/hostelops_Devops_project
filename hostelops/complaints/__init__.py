"""Complaints management blueprint (Module 2)."""
from flask import Blueprint

complaints_bp = Blueprint('complaints', __name__)

from hostelops.complaints import routes  # noqa: F401, E402

__all__ = ['complaints_bp']
