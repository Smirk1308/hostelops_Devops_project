"""Seed script to populate initial demo accounts."""
import os
import sys

# Ensure repository root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hostelops import create_app  # noqa: E402
from hostelops.extensions import db  # noqa: E402
from hostelops.models import User  # noqa: E402


def seed():
    """Create demo admin, staff, and student accounts if they do not exist."""
    app = create_app()
    with app.app_context():
        db.create_all()

        demo_users = [
            {
                'email': 'admin@hostelops.local',
                'name': 'Demo Admin',
                'role': 'admin',
                'room_no': None,
                'password': 'admin123',
            },
            {
                'email': 'staff@hostelops.local',
                'name': 'Demo Staff',
                'role': 'staff',
                'room_no': None,
                'password': 'staff123',
            },
            {
                'email': 'student@hostelops.local',
                'name': 'Demo Student',
                'role': 'student',
                'room_no': 'A-101',
                'password': 'student123',
            },
        ]

        created = 0
        for data in demo_users:
            existing = User.query.filter_by(email=data['email']).first()
            if not existing:
                user = User(
                    email=data['email'],
                    name=data['name'],
                    role=data['role'],
                    room_no=data['room_no'],
                )
                user.set_password(data['password'])
                db.session.add(user)
                created += 1
                print(f"Created {data['role']}: {data['email']}")
            else:
                print(f"Already exists: {data['email']}")

        db.session.commit()
        print(f"Seed complete. {created} user(s) created.")


if __name__ == '__main__':
    seed()
