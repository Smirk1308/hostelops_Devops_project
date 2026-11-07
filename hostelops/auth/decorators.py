"""Role-based authorization decorators for HostelOps."""
from functools import wraps
from flask import abort, current_app
from flask_login import current_user


def roles_required(*roles):
    """Enforce that current_user has one of the specified roles.

    If the user is not authenticated, delegates to Flask-Login's
    unauthorized handler. If the user's role is not among the allowed
    roles, aborts with 403 Forbidden.
    """
    allowed_roles = set()
    for role in roles:
        if isinstance(role, (list, tuple, set)):
            allowed_roles.update(role)
        else:
            allowed_roles.add(role)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                try:
                    return current_app.login_manager.unauthorized()
                except Exception:
                    abort(401)
            if getattr(current_user, 'role', None) not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Convenience alias for single-role checks
role_required = roles_required

__all__ = ['roles_required', 'role_required']
