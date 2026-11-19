"""Authentication routes and friendly application error pages."""
import re

from flask import flash, redirect, render_template, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from hostelops.auth import auth_bp
from hostelops.extensions import db
from hostelops.models import User


EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$"
)


def _valid_email(email):
    """Validate a practical ASCII email address and its component lengths."""
    if not EMAIL_PATTERN.fullmatch(email):
        return False
    local_part, domain = email.rsplit('@', 1)
    return (
        len(local_part) <= 64
        and len(domain) <= 253
        and not local_part.startswith('.')
        and not local_part.endswith('.')
        and '..' not in local_part
    )


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Register a student account."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        room_no = request.form.get('room_no', '').strip() or None

        if not name:
            flash('Name is required.', 'danger')
        elif len(name) > 100:
            flash('Name must be 100 characters or fewer.', 'danger')
        elif not email:
            flash('Email is required.', 'danger')
        elif len(email) > 120:
            flash('Email must be 120 characters or fewer.', 'danger')
        elif not _valid_email(email):
            flash('Enter a valid email address.', 'danger')
        elif User.query.filter(func.lower(User.email) == email).first():
            flash('An account with that email already exists.', 'danger')
        elif room_no and len(room_no) > 20:
            flash('Room number must be 20 characters or fewer.', 'danger')
        elif not password:
            flash('Password is required.', 'danger')
        elif len(password) < 8:
            flash('Password must contain at least 8 characters.', 'danger')
        elif password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            user = User(name=name, email=email, room_no=room_no, role='student')
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash('An account with that email already exists.', 'danger')
                return render_template('auth/register.html')
            flash('Registration successful. Please log in.', 'success')
            return redirect('/login')

    return render_template('auth/register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticate a user and accept only safe internal next URLs."""
    if current_user.is_authenticated:
        return redirect('/complaints')

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter(func.lower(User.email) == email).first()

        if user is None or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html'), 401

        login_user(user)
        next_url = request.args.get('next', '')
        safe_next = (
            next_url.startswith('/')
            and not next_url.startswith('//')
            and (len(next_url) == 1 or next_url[1] != '\\')
        )
        if safe_next:
            return redirect(next_url)
        return redirect('/complaints')

    return render_template('auth/login.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """End the current session."""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect('/login')


@auth_bp.app_errorhandler(403)
def forbidden(_error):
    """Render the friendly forbidden page."""
    return render_template('errors/403.html'), 403


@auth_bp.app_errorhandler(404)
def not_found(_error):
    """Render the friendly not found page."""
    return render_template('errors/404.html'), 404


__all__ = ['auth_bp']
