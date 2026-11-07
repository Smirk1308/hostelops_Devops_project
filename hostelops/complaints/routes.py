"""Complaint routes placeholder (to be implemented by Module 2)."""
from hostelops.complaints import complaints_bp

# Routes to be implemented by Module 2:
# GET / (redirects to /complaints)
# GET /complaints (student sees own; staff/admin see all with filters)
# GET/POST /complaints/new
# GET /complaints/<id>
# GET/POST /complaints/<id>/edit (owner student, Pending only)
# POST /complaints/<id>/delete (owner student while Pending, or admin)
# POST /complaints/<id>/assign (staff/admin)
# POST /complaints/<id>/status (staff/admin)

__all__ = ['complaints_bp']
