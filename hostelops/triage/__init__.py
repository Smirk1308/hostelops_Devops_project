"""Triage and analytics blueprint (Module 3)."""
from flask import Blueprint

triage_bp = Blueprint('triage', __name__)

from hostelops.triage import routes  # noqa: F401, E402

__all__ = ['triage_bp']
