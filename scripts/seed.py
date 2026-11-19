"""Seed demo data with explicit, environment-provided credentials only.

For local demonstrations, set HOSTELOPS_ENABLE_DEMO_SEED=1 and provide
HOSTELOPS_SEED_ADMIN_PASSWORD, HOSTELOPS_SEED_STAFF_PASSWORD, and
HOSTELOPS_SEED_STUDENT_PASSWORD. Each password must be at least 12 characters
and use at least three character groups. Never commit these values.
"""
import os
import sys
from datetime import timedelta

# Ensure repository root is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hostelops import create_app  # noqa: E402
from hostelops.extensions import db  # noqa: E402
from hostelops.models import Complaint, User, utcnow  # noqa: E402


SEED_OPT_IN = 'HOSTELOPS_ENABLE_DEMO_SEED'
PASSWORD_ENV_VARS = {
    'admin': 'HOSTELOPS_SEED_ADMIN_PASSWORD',
    'staff': 'HOSTELOPS_SEED_STAFF_PASSWORD',
    'student': 'HOSTELOPS_SEED_STUDENT_PASSWORD',
}
MIN_PASSWORD_LENGTH = 12


class SeedConfigurationError(ValueError):
    """Raised when demo seeding has not been explicitly configured."""


def load_demo_passwords(environ=None):
    """Return validated demo passwords without logging their values."""
    environment = os.environ if environ is None else environ
    missing = [
        variable for variable in PASSWORD_ENV_VARS.values()
        if not environment.get(variable)
    ]
    if missing:
        raise SeedConfigurationError(
            'Missing required demo password environment variables: '
            + ', '.join(missing)
        )
    if environment.get(SEED_OPT_IN) != '1':
        raise SeedConfigurationError(
            f"Set {SEED_OPT_IN}=1 to explicitly enable demo seeding."
        )

    passwords = {}
    for role, variable in PASSWORD_ENV_VARS.items():
        password = environment.get(variable)
        character_groups = (
            any(char.islower() for char in password),
            any(char.isupper() for char in password),
            any(char.isdigit() for char in password),
            any(not char.isalnum() for char in password),
        )
        if (len(password) < MIN_PASSWORD_LENGTH
                or sum(character_groups) < 3):
            raise SeedConfigurationError(
                f'{variable} must be at least {MIN_PASSWORD_LENGTH} characters '
                'and include at least three character groups '
                '(lowercase, uppercase, digits, symbols).'
            )
        passwords[role] = password
    return passwords


DEMO_COMPLAINTS = [
    {
        'title': 'No water supply in Block A bathrooms',
        'description': (
            'There has been no water in the Block A bathroom taps since yesterday '
            'morning, affecting several rooms on the first floor.'
        ),
        'category': 'Water', 'priority': 'High', 'status': 'Pending',
        'age_days': 4, 'resolution_days': None,
    },
    {
        'title': 'Sparks from the corridor switchboard',
        'description': (
            'The switchboard beside room A-108 sparked twice when someone plugged '
            'in a phone charger. Please isolate and inspect it.'
        ),
        'category': 'Electricity', 'priority': 'High', 'status': 'Pending',
        'age_days': 3, 'resolution_days': None,
    },
    {
        'title': 'Wi-Fi drops on the second floor',
        'description': (
            'The hostel network disconnects every few minutes in the second-floor '
            'study area, especially in the evening.'
        ),
        'category': 'Wi-Fi', 'priority': 'Medium', 'status': 'Pending',
        'age_days': 0, 'resolution_days': None,
    },
    {
        'title': 'Stale food served at dinner',
        'description': (
            'Several students noticed a sour smell from the paneer served at '
            'dinner in the mess today. Please check food storage.'
        ),
        'category': 'Mess', 'priority': 'High', 'status': 'Pending',
        'age_days': 0, 'resolution_days': None,
    },
    {
        'title': 'Washroom cleaning on ground floor',
        'description': (
            'The ground-floor washroom near the common room needs cleaning and '
            'the overflowing bin should be emptied.'
        ),
        'category': 'Cleanliness', 'priority': 'Low', 'status': 'Pending',
        'age_days': 0, 'resolution_days': None,
    },
    {
        'title': 'Leak under the third-floor basin',
        'description': (
            'Water is leaking steadily from the pipe below the third-floor '
            'washbasin and pooling near the doorway.'
        ),
        'category': 'Water', 'priority': 'High', 'status': 'In Progress',
        'age_days': 5, 'resolution_days': None,
    },
    {
        'title': 'Ceiling light out in stairwell B',
        'description': (
            'The light between the second and third floors of stairwell B is not '
            'working, making the stairs difficult to use at night.'
        ),
        'category': 'Electricity', 'priority': 'Medium', 'status': 'In Progress',
        'age_days': 3, 'resolution_days': None,
    },
    {
        'title': 'Mess handwash tap has low pressure',
        'description': (
            'Only a thin stream comes from the handwash tap outside the dining '
            'hall, so students are queuing to wash their hands.'
        ),
        'category': 'Water', 'priority': 'Medium', 'status': 'In Progress',
        'age_days': 0, 'resolution_days': None,
    },
    {
        'title': 'Broken chair in room A-204',
        'description': (
            'The back support on the wooden chair in room A-204 has come loose '
            'and it wobbles when used at the desk.'
        ),
        'category': 'Furniture', 'priority': 'Low', 'status': 'In Progress',
        'age_days': 0, 'resolution_days': None,
    },
    {
        'title': 'Request for additional notice boards',
        'description': (
            'Could a notice board be installed beside the second-floor common '
            'room for club and hostel announcements?'
        ),
        'category': 'Other', 'priority': 'Low', 'status': 'In Progress',
        'age_days': 0, 'resolution_days': None,
    },
    {
        'title': 'Study room access point repaired',
        'description': (
            'The Wi-Fi access point in the study room was unreachable from most '
            'desks; service returned after its power connection was reset.'
        ),
        'category': 'Wi-Fi', 'priority': 'Medium', 'status': 'Resolved',
        'age_days': 7, 'resolution_days': 5,
    },
    {
        'title': 'Dining hall fan regulator replaced',
        'description': (
            'The dining hall fan was stuck at its highest speed. Maintenance '
            'replaced the faulty regulator and the fan now adjusts normally.'
        ),
        'category': 'Electricity', 'priority': 'Low', 'status': 'Resolved',
        'age_days': 6, 'resolution_days': 4,
    },
    {
        'title': 'Dining tables cleaned after lunch',
        'description': (
            'Food residue was left on the tables after lunch service. The mess '
            'team cleaned the dining area before the evening meal.'
        ),
        'category': 'Cleanliness', 'priority': 'Low', 'status': 'Resolved',
        'age_days': 5, 'resolution_days': 3,
    },
    {
        'title': 'Cupboard hinge in room A-116 fixed',
        'description': (
            'The upper hinge on the cupboard door had pulled away from the '
            'frame. A replacement hinge was fitted and the door closes safely.'
        ),
        'category': 'Furniture', 'priority': 'Medium', 'status': 'Resolved',
        'age_days': 8, 'resolution_days': 6,
    },
    {
        'title': 'Mess menu displayed for the week',
        'description': (
            'The weekly menu was missing from the dining hall entrance. A new '
            'printed copy has been posted on the information board.'
        ),
        'category': 'Mess', 'priority': 'Low', 'status': 'Resolved',
        'age_days': 4, 'resolution_days': 2,
    },
]


def seed():
    """Create demo accounts and seed complaints only in an empty table."""
    passwords = load_demo_passwords()
    app = create_app()
    with app.app_context():
        db.create_all()

        demo_users = [
            {
                'email': 'admin@hostelops.local',
                'name': 'Demo Admin',
                'role': 'admin',
                'room_no': None,
            },
            {
                'email': 'staff@hostelops.local',
                'name': 'Demo Staff',
                'role': 'staff',
                'room_no': None,
            },
            {
                'email': 'student@hostelops.local',
                'name': 'Demo Student',
                'role': 'student',
                'room_no': 'A-101',
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
                user.set_password(passwords[data['role']])
                db.session.add(user)
                created += 1
                print(f"Created {data['role']}: {data['email']}")
            else:
                print(f"Already exists: {data['email']}")

        db.session.commit()
        print(f"Seed complete. {created} user(s) created.")

        student = User.query.filter_by(
            email='student@hostelops.local'
        ).one()
        staff = User.query.filter_by(email='staff@hostelops.local').one()

        if Complaint.query.count():
            print('Seed complete. 0 complaint(s) created; complaints already exist.')
            return

        now = utcnow()
        complaints = []
        for item in DEMO_COMPLAINTS:
            created_at = now - timedelta(
                days=item['age_days'] if item['age_days'] else 0,
                hours=0 if item['age_days'] else 8,
            )
            resolved_at = None
            if item['resolution_days'] is not None:
                resolved_at = now - timedelta(days=item['resolution_days'])

            assigned_to = (
                staff.id if item['status'] in ('In Progress', 'Resolved') else None
            )
            complaints.append(Complaint(
                title=item['title'],
                description=item['description'],
                category=item['category'],
                priority=item['priority'],
                status=item['status'],
                created_by=student.id,
                assigned_to=assigned_to,
                created_at=created_at,
                resolved_at=resolved_at,
            ))

        db.session.add_all(complaints)
        db.session.commit()
        print(f'Seed complete. {len(complaints)} complaint(s) created.')


if __name__ == '__main__':
    try:
        seed()
    except SeedConfigurationError as error:
        sys.exit(str(error))
