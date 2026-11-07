"""Data models for HostelOps."""
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from hostelops.extensions import db

CATEGORIES = [
    'Water',
    'Electricity',
    'Wi-Fi',
    'Mess',
    'Cleanliness',
    'Furniture',
    'Other',
]

PRIORITIES = ['Low', 'Medium', 'High']
STATUSES = ['Pending', 'In Progress', 'Resolved']
ROLES = ['student', 'staff', 'admin']


def utcnow():
    """Return naive UTC datetime for database timestamp consistency."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(UserMixin, db.Model):
    """User account model supporting student, staff, and admin roles."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    room_no = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    def set_password(self, password):
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify candidate password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Complaint(db.Model):
    """Complaint model tracking issue details, status, and assignment."""

    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='Medium')
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_by = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False
    )
    assigned_to = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=True
    )
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
    resolved_at = db.Column(db.DateTime, nullable=True)

    creator = db.relationship(
        'User',
        foreign_keys=[created_by],
        backref=db.backref('complaints_created', lazy=True),
    )
    assignee = db.relationship(
        'User',
        foreign_keys=[assigned_to],
        backref=db.backref('complaints_assigned', lazy=True),
    )

    def __repr__(self):
        return f'<Complaint {self.id}: {self.title} [{self.status}]>'
