"""Tests for Module 3: triage ML, predictor, suggest API, stats, dashboard."""
import pytest
from flask import g

from hostelops.extensions import db
from hostelops.models import CATEGORIES, PRIORITIES, STATUSES, Complaint, User, utcnow


# ---------------------------------------------------------------------------
# Local fixtures (make_user and login_as)
# ---------------------------------------------------------------------------

@pytest.fixture
def make_user(app):
    counter = {'n': 0}

    def _make_user(role='student', email=None, password='password123'):
        counter['n'] += 1
        n = counter['n']
        user = User(
            name=f'Test {role} {n}',
            email=email or f'{role}{n}@test.local',
            role=role,
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    return _make_user


@pytest.fixture
def login_as():
    def _login_as(client, user):
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        g.pop('_login_user', None)

    return _login_as


# ---------------------------------------------------------------------------
# Module-scoped model fixture + autouse cache-clear
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def model_file(tmp_path_factory):
    """Train the model once per module and return the path."""
    import ml.train as ml_train
    out = tmp_path_factory.mktemp('ml') / 'model.joblib'
    ml_train.train(model_path=out)
    return out


@pytest.fixture(autouse=True)
def clear_predictor_cache():
    """Clear predictor cache before every test."""
    from hostelops.triage import predictor
    predictor.clear_cache()


# ---------------------------------------------------------------------------
# Part A: dataset tests
# ---------------------------------------------------------------------------

class TestDataset:
    def test_csv_columns(self):
        import pandas as pd
        import pathlib
        csv = (
            pathlib.Path(__file__).resolve().parents[1]
            / 'ml' / 'data' / 'complaints.csv'
        )
        df = pd.read_csv(csv)
        assert list(df.columns) == ['text', 'category', 'priority']

    def test_min_rows_per_category(self):
        import pandas as pd
        import pathlib
        csv = (
            pathlib.Path(__file__).resolve().parents[1]
            / 'ml' / 'data' / 'complaints.csv'
        )
        df = pd.read_csv(csv)
        counts = df['category'].value_counts()
        for cat in CATEGORIES:
            assert cat in counts.index, f'Missing category: {cat}'
            assert counts[cat] >= 40, (
                f'{cat} has only {counts[cat]} rows (need >= 40)'
            )

    def test_valid_categories_and_priorities(self):
        import pandas as pd
        import pathlib
        csv = (
            pathlib.Path(__file__).resolve().parents[1]
            / 'ml' / 'data' / 'complaints.csv'
        )
        df = pd.read_csv(csv)
        assert set(df['category'].unique()).issubset(set(CATEGORIES))
        assert set(df['priority'].unique()).issubset(set(PRIORITIES))


# ---------------------------------------------------------------------------
# Part A: training tests
# ---------------------------------------------------------------------------

class TestTraining:
    def test_train_returns_good_accuracy(self, model_file):
        import ml.train as ml_train
        result = ml_train.train(model_path=model_file)
        assert result['category_accuracy'] >= 0.80, (
            f"Category accuracy too low: {result['category_accuracy']}"
        )
        assert result['priority_accuracy'] >= 0.80, (
            f"Priority accuracy too low: {result['priority_accuracy']}"
        )

    def test_model_file_exists(self, model_file):
        assert model_file.exists()


# ---------------------------------------------------------------------------
# Part B: predictor tests
# ---------------------------------------------------------------------------

class TestPredictor:
    def test_water_complaint(self, model_file):
        from hostelops.triage import predictor
        cat, pri, conf = predictor.suggest(
            'no water in block B since last night',
            model_path=str(model_file),
        )
        assert cat == 'Water'

    def test_electricity_complaint(self, model_file):
        from hostelops.triage import predictor
        cat, pri, conf = predictor.suggest(
            'sparks coming from the switch board in my room',
            model_path=str(model_file),
        )
        assert cat == 'Electricity'

    def test_blank_text(self, model_file):
        from hostelops.triage import predictor
        assert predictor.suggest('', model_path=str(model_file)) == (
            None, None, 0.0
        )

    def test_short_text(self, model_file):
        from hostelops.triage import predictor
        assert predictor.suggest('abc', model_path=str(model_file)) == (
            None, None, 0.0
        )

    def test_missing_model(self, tmp_path):
        from hostelops.triage import predictor
        missing = str(tmp_path / 'nonexistent.joblib')
        assert predictor.suggest(
            'no water in block A', model_path=missing
        ) == (None, None, 0.0)

    def test_confidence_range(self, model_file):
        from hostelops.triage import predictor
        _, _, conf = predictor.suggest(
            'no water in block B since last night',
            model_path=str(model_file),
        )
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0


# ---------------------------------------------------------------------------
# Part B: suggest API tests
# ---------------------------------------------------------------------------

class TestSuggestAPI:
    def test_logged_in_student_200(self, app, client, make_user, login_as,
                                   model_file):
        app.config['MODEL_PATH'] = str(model_file)
        user = make_user(role='student')
        login_as(client, user)
        resp = client.post(
            '/api/triage/suggest',
            json={'text': 'no water in block B since last night'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'category' in data
        assert 'priority' in data
        assert 'confidence' in data

    def test_invalid_json_400(self, client, make_user, login_as):
        user = make_user(role='student')
        login_as(client, user)
        resp = client.post(
            '/api/triage/suggest',
            data='not json',
            content_type='text/plain',
        )
        assert resp.status_code == 400

    def test_missing_text_key_400(self, client, make_user, login_as):
        user = make_user(role='student')
        login_as(client, user)
        resp = client.post('/api/triage/suggest', json={'other': 'value'})
        assert resp.status_code == 400

    def test_unauthenticated_401(self, client):
        resp = client.post(
            '/api/triage/suggest',
            json={'text': 'no water in block B'},
        )
        assert resp.status_code == 401
        assert resp.get_json().get('error')


# ---------------------------------------------------------------------------
# Part C: stats API tests
# ---------------------------------------------------------------------------

class TestStatsAPI:
    def _make_complaint(self, user, category='Water', status='Pending',
                        created_at=None):
        """Create and persist a complaint directly."""
        c = Complaint(
            title=f'Test {category}',
            description=f'Test complaint about {category}',
            category=category,
            priority='Medium',
            status=status,
            created_by=user.id,
        )
        if created_at is not None:
            c.created_at = created_at
        db.session.add(c)
        db.session.commit()
        return c

    def test_counts_and_zero_fill(self, app, client, make_user, login_as):
        staff = make_user(role='staff')
        # Create one Water Pending, one Electricity Resolved
        self._make_complaint(staff, category='Water', status='Pending')
        self._make_complaint(staff, category='Electricity', status='Resolved')
        login_as(client, staff)
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['by_category']['Water'] == 1
        assert data['by_category']['Electricity'] == 1
        # Other categories should be zero
        for cat in CATEGORIES:
            if cat not in ('Water', 'Electricity'):
                assert data['by_category'][cat] == 0
        # All statuses present
        for s in STATUSES:
            assert s in data['by_status']

    def test_overdue_count(self, app, client, make_user, login_as):
        from datetime import timedelta
        staff = make_user(role='staff')
        old_time = utcnow() - timedelta(days=3)
        # An old Pending complaint — should be overdue (default 48 h)
        self._make_complaint(staff, status='Pending', created_at=old_time)
        login_as(client, staff)
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        assert resp.get_json()['overdue'] >= 1

    def test_student_gets_403(self, client, make_user, login_as):
        student = make_user(role='student')
        login_as(client, student)
        resp = client.get('/api/stats')
        assert resp.status_code == 403
        assert resp.get_json().get('error')

    def test_unauthenticated_gets_401(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 401
        assert resp.get_json().get('error')


# ---------------------------------------------------------------------------
# Part C: dashboard tests
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_staff_gets_200(self, client, make_user, login_as):
        staff = make_user(role='staff')
        login_as(client, staff)
        resp = client.get('/dashboard')
        assert resp.status_code == 200
        assert b'categoryChart' in resp.data

    def test_admin_gets_200(self, client, make_user, login_as):
        admin = make_user(role='admin')
        login_as(client, admin)
        resp = client.get('/dashboard')
        assert resp.status_code == 200

    def test_student_gets_403(self, client, make_user, login_as):
        student = make_user(role='student')
        login_as(client, student)
        resp = client.get('/dashboard')
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Part C: is_overdue tests
# ---------------------------------------------------------------------------

class TestIsOverdue:
    def _complaint(self, status, created_at):
        """Build a plain-object complaint (not persisted) for is_overdue tests."""
        class FakeComplaint:
            pass
        c = FakeComplaint()
        c.status = status
        c.created_at = created_at
        return c

    def test_exactly_at_limit_not_overdue(self, app):
        from datetime import timedelta
        from hostelops.triage.overdue import is_overdue
        now = utcnow()
        # Exactly 48 h old — NOT overdue (strict >)
        c = self._complaint('Pending', now - timedelta(hours=48))
        assert not is_overdue(c, now=now)

    def test_just_over_limit_is_overdue(self, app):
        from datetime import timedelta
        from hostelops.triage.overdue import is_overdue
        now = utcnow()
        # 48 h + 1 s — overdue
        c = self._complaint('Pending', now - timedelta(hours=48, seconds=1))
        assert is_overdue(c, now=now)

    def test_resolved_never_overdue(self, app):
        from datetime import timedelta
        from hostelops.triage.overdue import is_overdue
        now = utcnow()
        # Resolved, even if old
        c = self._complaint('Resolved', now - timedelta(days=10))
        assert not is_overdue(c, now=now)

    def test_custom_overdue_hours(self, app):
        from datetime import timedelta
        from hostelops.triage.overdue import is_overdue
        app.config['OVERDUE_HOURS'] = 1
        now = utcnow()
        # 1 h + 1 s old with 1-hour threshold — overdue
        c = self._complaint('Pending', now - timedelta(hours=1, seconds=1))
        assert is_overdue(c, now=now)
        # Reset to avoid affecting other tests
        app.config['OVERDUE_HOURS'] = 48
