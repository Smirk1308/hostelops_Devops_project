"""Overdue complaint detection logic (Module 3)."""
import os
from datetime import datetime, timezone
from flask import current_app


def is_overdue(complaint, now=None) -> bool:
    """Check if a complaint has exceeded the overdue time limit.

    Returns True when status is 'Pending' or 'In Progress' and the elapsed
    time since created_at strictly exceeds OVERDUE_HOURS (default 48).
    """
    if complaint is None:
        return False

    status = getattr(complaint, 'status', None)
    if status not in ('Pending', 'In Progress'):
        return False

    created_at = getattr(complaint, 'created_at', None)
    if created_at is None:
        return False

    try:
        overdue_hours = current_app.config.get('OVERDUE_HOURS', 48)
    except RuntimeError:
        overdue_hours = int(os.environ.get('OVERDUE_HOURS', 48))

    try:
        overdue_hours = float(overdue_hours)
    except (TypeError, ValueError):
        overdue_hours = 48.0

    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
    elif getattr(now, 'tzinfo', None) is not None:
        now = now.astimezone(timezone.utc).replace(tzinfo=None)

    if getattr(created_at, 'tzinfo', None) is not None:
        created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)

    age_seconds = (now - created_at).total_seconds()
    return age_seconds > (overdue_hours * 3600.0)


__all__ = ['is_overdue']
