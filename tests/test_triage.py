"""Tests for Module 3: triage ML, predictor, suggest API, stats, dashboard."""
from datetime import timedelta
import pathlib

import pytest

from hostelops.extensions import db
from hostelops.models import CATEGORIES, PRIORITIES, STATUSES, Complaint, utcnow


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
# Part P: Dataset Tests
# ---------------------------------------------------------------------------

class TestDataset:
    def _load_csv(self):
        import pandas as pd
        csv = (
            pathlib.Path(__file__).resolve().parents[1]
            / 'ml' / 'data' / 'complaints.csv'
        )
        return pd.read_csv(csv)

    def test_csv_columns(self):
        df = self._load_csv()
        assert list(df.columns) == ['text', 'category', 'priority']

    def test_row_count_range(self):
        df = self._load_csv()
        assert 300 <= len(df) <= 450, f'Expected ~350 rows, got {len(df)}'

    def test_min_rows_per_category(self):
        df = self._load_csv()
        counts = df['category'].value_counts()
        for cat in CATEGORIES:
            assert cat in counts.index, f'Missing category: {cat}'
            assert counts[cat] >= 40, (
                f'{cat} has only {counts[cat]} rows (need >= 40)'
            )

    def test_valid_categories_and_priorities(self):
        df = self._load_csv()
        assert set(df['category'].unique()).issubset(set(CATEGORIES))
        assert set(df['priority'].unique()).issubset(set(PRIORITIES))

    def test_no_empty_text(self):
        df = self._load_csv()
        assert not df['text'].isna().any()
        assert (df['text'].str.strip() != '').all()

    def test_no_duplicate_descriptions(self):
        df = self._load_csv()
        assert not df['text'].duplicated().any(), 'Duplicate texts found'

    def test_deterministic_generation(self, tmp_path):
        import ml.generate_data as gd
        out1 = tmp_path / 'c1.csv'
        out2 = tmp_path / 'c2.csv'
        df1 = gd.generate(output_path=out1)
        df2 = gd.generate(output_path=out2)
        assert df1.equals(df2), 'Dataset generation is non-deterministic'


# ---------------------------------------------------------------------------
# Part Q: Training Tests
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

    def test_saved_model_structure(self, model_file):
        import joblib
        saved = joblib.load(model_file)
        assert isinstance(saved, dict)
        assert 'category' in saved
        assert 'priority' in saved
        assert hasattr(saved['category'], 'predict')
        assert hasattr(saved['priority'], 'predict')

    def test_custom_csv_and_output_path(self, tmp_path):
        import ml.train as ml_train
        import pandas as pd
        csv_path = tmp_path / 'custom.csv'
        custom_model = tmp_path / 'custom_model.joblib'
        df = pd.DataFrame([
            {
                'text': f'No water in room {i}',
                'category': 'Water',
                'priority': 'High',
            }
            for i in range(10)
        ] + [
            {
                'text': f'Fan broken in room {i}',
                'category': 'Electricity',
                'priority': 'Low',
            }
            for i in range(10)
        ])
        df.to_csv(csv_path, index=False)
        result = ml_train.train(csv_path=csv_path, model_path=custom_model)
        assert custom_model.exists()
        assert 'category_accuracy' in result
        assert 'priority_accuracy' in result


# ---------------------------------------------------------------------------
# Part R: Predictor Tests
# ---------------------------------------------------------------------------

class TestPredictor:
    def test_water_complaint(self, model_file):
        from hostelops.triage import predictor
        cat, pri, conf = predictor.suggest(
            'no water in block B since last night',
            model_path=str(model_file),
        )
        assert cat == 'Water'
        assert pri in PRIORITIES

    def test_electricity_complaint(self, model_file):
        from hostelops.triage import predictor
        cat, pri, conf = predictor.suggest(
            'sparks coming from the switch board in my room',
            model_path=str(model_file),
        )
        assert cat == 'Electricity'
        assert pri in PRIORITIES

    def test_wifi_complaint(self, model_file):
        from hostelops.triage import predictor
        cat, pri, conf = predictor.suggest(
            'hostel wifi router offline cannot connect to internet',
            model_path=str(model_file),
        )
        assert cat == 'Wi-Fi'

    def test_high_priority_complaint(self, model_file):
        from hostelops.triage import predictor
        _, pri, _ = predictor.suggest(
            'Electric shock from socket in block A',
            model_path=str(model_file),
        )
        assert pri == 'High'

    def test_low_priority_complaint(self, model_file):
        from hostelops.triage import predictor
        _, pri, _ = predictor.suggest(
            'Please add a notice board near block A',
            model_path=str(model_file),
        )
        assert pri == 'Low'

    def test_blank_text(self, model_file):
        from hostelops.triage import predictor
        assert predictor.suggest('', model_path=str(model_file)) == (
            None, None, 0.0
        )
        assert predictor.suggest('   ', model_path=str(model_file)) == (
            None, None, 0.0
        )

    def test_short_text(self, model_file):
        from hostelops.triage import predictor
        assert predictor.suggest('abc', model_path=str(model_file)) == (
            None, None, 0.0
        )

    def test_invalid_input_type(self, model_file):
        from hostelops.triage import predictor
        m = str(model_file)
        assert predictor.suggest(None, model_path=m) == (None, None, 0.0)
        assert predictor.suggest(12345, model_path=m) == (None, None, 0.0)
        assert predictor.suggest(['text'], model_path=m) == (None, None, 0.0)

    def test_missing_model(self, tmp_path):
        from hostelops.triage import predictor
        missing = str(tmp_path / 'nonexistent.joblib')
        assert predictor.suggest(
            'no water in block A', model_path=missing
        ) == (None, None, 0.0)

    def test_corrupt_model_file(self, tmp_path):
        from hostelops.triage import predictor
        corrupt = tmp_path / 'corrupt.joblib'
        corrupt.write_text('not a joblib file')
        assert predictor.suggest(
            'no water in block A', model_path=str(corrupt)
        ) == (None, None, 0.0)

    def test_confidence_range(self, model_file):
        from hostelops.triage import predictor
        cat, pri, conf = predictor.suggest(
            'no water in block B since last night',
            model_path=str(model_file),
        )
        assert isinstance(conf, float)
        assert 0.0 <= conf <= 1.0
        assert cat in CATEGORIES
        assert pri in PRIORITIES

    def test_model_cache_behaviour(self, model_file):
        from hostelops.triage import predictor
        m1 = predictor.load_model(str(model_file))
        m2 = predictor.load_model(str(model_file))
        assert m1 is m2, 'Model should be cached on subsequent loads'


# ---------------------------------------------------------------------------
# Part S: Suggest API Tests
# ---------------------------------------------------------------------------

class TestSuggestAPI:
    def test_authenticated_student_200(self, app, client, make_user, login_as,
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
        assert data['category'] in CATEGORIES
        assert data['priority'] in PRIORITIES
        assert isinstance(data['confidence'], float)

    def test_authenticated_staff_200(self, app, client, make_user, login_as,
                                     model_file):
        app.config['MODEL_PATH'] = str(model_file)
        staff = make_user(role='staff')
        login_as(client, staff)
        resp = client.post(
            '/api/triage/suggest',
            json={'text': 'Tube light in block B needs replacing'},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['category'] in CATEGORIES

    def test_authenticated_admin_200(self, app, client, make_user, login_as,
                                     model_file):
        app.config['MODEL_PATH'] = str(model_file)
        admin = make_user(role='admin')
        login_as(client, admin)
        resp = client.post(
            '/api/triage/suggest',
            json={'text': 'Power cut in block A since this morning'},
        )
        assert resp.status_code == 200

    def test_unauthenticated_401(self, client):
        resp = client.post(
            '/api/triage/suggest',
            json={'text': 'no water in block B'},
        )
        assert resp.status_code == 401
        assert resp.get_json().get('error') == 'Authentication required'

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

    def test_non_string_text_400(self, client, make_user, login_as):
        user = make_user(role='student')
        login_as(client, user)
        resp = client.post('/api/triage/suggest', json={'text': 12345})
        assert resp.status_code == 400

    def test_blank_text_handled_safely(self, app, client, make_user, login_as,
                                       model_file):
        app.config['MODEL_PATH'] = str(model_file)
        user = make_user(role='student')
        login_as(client, user)
        resp = client.post('/api/triage/suggest', json={'text': '   '})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['category'] is None
        assert data['priority'] is None
        assert data['confidence'] == 0.0

    def test_missing_model_returns_null_and_zero_conf(
        self, app, client, make_user, login_as, tmp_path
    ):
        app.config['MODEL_PATH'] = str(tmp_path / 'missing.joblib')
        user = make_user(role='student')
        login_as(client, user)
        resp = client.post(
            '/api/triage/suggest', json={'text': 'No water in block A'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['category'] is None
        assert data['priority'] is None
        assert data['confidence'] == 0.0


# ---------------------------------------------------------------------------
# Part T: Overdue Tests
# ---------------------------------------------------------------------------

class TestIsOverdue:
    def _complaint(self, status, created_at):
        """Build a plain-object complaint for duck-typed is_overdue tests."""
        class FakeComplaint:
            pass
        c = FakeComplaint()
        c.status = status
        c.created_at = created_at
        return c

    def test_exactly_at_limit_not_overdue(self, app):
        from hostelops.triage.overdue import is_overdue
        now = utcnow()
        # Exactly 48 h old — NOT overdue (strict >)
        c = self._complaint('Pending', now - timedelta(hours=48))
        assert not is_overdue(c, now=now)

    def test_just_over_limit_is_overdue(self, app):
        from hostelops.triage.overdue import is_overdue
        now = utcnow()
        # 48 h + 1 s — overdue
        c = self._complaint('Pending', now - timedelta(hours=48, seconds=1))
        assert is_overdue(c, now=now)

    def test_resolved_never_overdue(self, app):
        from hostelops.triage.overdue import is_overdue
        now = utcnow()
        c = self._complaint('Resolved', now - timedelta(days=10))
        assert not is_overdue(c, now=now)

    def test_in_progress_can_be_overdue(self, app):
        from hostelops.triage.overdue import is_overdue
        now = utcnow()
        c = self._complaint('In Progress', now - timedelta(hours=49))
        assert is_overdue(c, now=now)

    def test_custom_overdue_hours(self, app):
        from hostelops.triage.overdue import is_overdue
        app.config['OVERDUE_HOURS'] = 1
        now = utcnow()
        c = self._complaint('Pending', now - timedelta(hours=1, seconds=1))
        assert is_overdue(c, now=now)
        app.config['OVERDUE_HOURS'] = 48

    def test_missing_created_at_handled_safely(self, app):
        from hostelops.triage.overdue import is_overdue
        c = self._complaint('Pending', None)
        assert not is_overdue(c)

    def test_none_complaint_returns_false(self, app):
        from hostelops.triage.overdue import is_overdue
        assert not is_overdue(None)


# ---------------------------------------------------------------------------
# Part U: Stats API Tests
# ---------------------------------------------------------------------------

class TestStatsAPI:
    def _make_complaint(self, user, category='Water', status='Pending',
                        created_at=None, title='Test Complaint'):
        c = Complaint(
            title=title,
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

    def test_staff_can_access_stats(self, client, make_user, login_as):
        staff = make_user(role='staff')
        login_as(client, staff)
        resp = client.get('/api/stats')
        assert resp.status_code == 200

    def test_admin_can_access_stats(self, client, make_user, login_as):
        admin = make_user(role='admin')
        login_as(client, admin)
        resp = client.get('/api/stats')
        assert resp.status_code == 200

    def test_student_gets_403(self, client, make_user, login_as):
        student = make_user(role='student')
        login_as(client, student)
        resp = client.get('/api/stats')
        assert resp.status_code == 403

    def test_unauthenticated_gets_401(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code == 401

    def test_category_and_status_counts(self, client, make_user, login_as):
        staff = make_user(role='staff')
        self._make_complaint(staff, category='Water', status='Pending')
        self._make_complaint(staff, category='Water', status='In Progress')
        self._make_complaint(staff, category='Electricity', status='Resolved')
        login_as(client, staff)
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['by_category']['Water'] == 2
        assert data['by_category']['Electricity'] == 1
        assert data['by_status']['Pending'] == 1
        assert data['by_status']['In Progress'] == 1
        assert data['by_status']['Resolved'] == 1

    def test_zero_count_categories_and_statuses_included(self, client, make_user,
                                                         login_as):
        staff = make_user(role='staff')
        login_as(client, staff)
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        for cat in CATEGORIES:
            assert cat in data['by_category']
            assert data['by_category'][cat] == 0
        for s in STATUSES:
            assert s in data['by_status']
            assert data['by_status'][s] == 0

    def test_overdue_count_and_resolved_excluded(self, client, make_user, login_as):
        staff = make_user(role='staff')
        old_time = utcnow() - timedelta(days=3)
        self._make_complaint(staff, status='Pending', created_at=old_time)
        self._make_complaint(staff, status='In Progress', created_at=old_time)
        # Resolved complaint from 5 days ago must NOT be counted as overdue
        five_days_ago = utcnow() - timedelta(days=5)
        self._make_complaint(staff, status='Resolved', created_at=five_days_ago)
        login_as(client, staff)
        resp = client.get('/api/stats')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['overdue'] == 2

    def test_overdue_list_ordered_longest_open_first(
        self, client, make_user, login_as
    ):
        from hostelops.triage.routes import _collect_stats
        staff = make_user(role='staff')
        now = utcnow()
        c_older = self._make_complaint(
            staff, title='Older', status='Pending', created_at=now - timedelta(days=4)
        )
        c_newer = self._make_complaint(
            staff, title='Newer', status='Pending', created_at=now - timedelta(days=3)
        )
        stats = _collect_stats()
        ids = [item['id'] for item in stats['overdue_list']]
        assert ids.index(c_older.id) < ids.index(c_newer.id), (
            'Longest-open should appear first'
        )


# ---------------------------------------------------------------------------
# Part V: Dashboard Tests
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_staff_can_access_dashboard(self, client, make_user, login_as):
        staff = make_user(role='staff')
        login_as(client, staff)
        resp = client.get('/dashboard')
        assert resp.status_code == 200

    def test_admin_can_access_dashboard(self, client, make_user, login_as):
        admin = make_user(role='admin')
        login_as(client, admin)
        resp = client.get('/dashboard')
        assert resp.status_code == 200

    def test_student_gets_403(self, client, make_user, login_as):
        student = make_user(role='student')
        login_as(client, student)
        resp = client.get('/dashboard')
        assert resp.status_code == 403

    def test_dashboard_displays_required_headings_and_charts(
        self, client, make_user, login_as
    ):
        staff = make_user(role='staff')
        login_as(client, staff)
        resp = client.get('/dashboard')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Operations Dashboard' in html
        assert 'categoryChart' in html
        assert 'statusChart' in html
        assert 'Attention Required' in html

    def test_dashboard_displays_summary_counts(self, client, make_user, login_as):
        staff = make_user(role='staff')
        Complaint(
            title='Test Water',
            description='desc',
            category='Water',
            priority='Medium',
            status='Pending',
            created_by=staff.id,
        )
        db.session.commit()
        login_as(client, staff)
        resp = client.get('/dashboard')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Total Complaints' in html

    def test_dashboard_handles_empty_database(self, client, make_user, login_as):
        staff = make_user(role='staff')
        login_as(client, staff)
        resp = client.get('/dashboard')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'All caught up!' in html
        assert 'No overdue complaints require attention right now.' in html

    def test_dashboard_displays_overdue_complaints(self, client, make_user, login_as):
        staff = make_user(role='staff')
        old_time = utcnow() - timedelta(days=3)
        c = Complaint(
            title='Leaking Main Pipe',
            description='Severe water leak in block B',
            category='Water',
            priority='High',
            status='Pending',
            created_by=staff.id,
            created_at=old_time,
        )
        db.session.add(c)
        db.session.commit()
        login_as(client, staff)
        resp = client.get('/dashboard')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Leaking Main Pipe' in html
        assert f'/complaints/{c.id}' in html
