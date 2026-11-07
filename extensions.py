"""Root extensions module for re-exporting."""
from hostelops.extensions import csrf, db, login_manager

__all__ = ['db', 'login_manager', 'csrf']
