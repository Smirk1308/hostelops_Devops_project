# HostelOps SPEC (exact contracts)

## Config (env vars, with defaults)
SECRET_KEY (dev default), DATABASE_URL (sqlite:///hostelops.db), OVERDUE_HOURS (48), MODEL_PATH (ml/model.joblib), APP_VERSION (0.1.0).
Libraries: Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF (CSRFProtect), werkzeug.security for password hashing, scikit-learn, pandas, joblib, gunicorn, pytest, flake8.

## Data models (hostelops/models.py)
User: id, name, email (unique), password_hash, role ('student'|'staff'|'admin'), room_no (nullable), created_at.
Complaint: id, title, description, category, priority ('Low'|'Medium'|'High'), status ('Pending'|'In Progress'|'Resolved'), created_by (FK User), assigned_to (FK User, nullable), created_at, updated_at, resolved_at (nullable).
Categories: Water, Electricity, Wi-Fi, Mess, Cleanliness, Furniture, Other.

## Shared helpers (provided by the foundation, owned by the modules named)
- hostelops/auth/decorators.py: roles_required(*roles) (Module 1)
- hostelops/triage/overdue.py: is_overdue(complaint, now=None) -> bool. True when status is Pending or In Progress and age exceeds OVERDUE_HOURS. (Module 3)
- templates/base.html with blocks `title` and `content`; static/css/style.css (Module 1)

## Routes
Health: GET /health -> {"status": "ok", "version": APP_VERSION}
Auth (Module 1): GET/POST /register, GET/POST /login, POST /logout, GET /admin/users (admin), POST /admin/users/<id>/role (admin), POST /admin/staff (admin creates staff account).
Complaints (Module 2): GET / (redirects to /complaints), GET /complaints (student sees own; staff/admin see all with filters ?status=&category=&priority=), GET/POST /complaints/new, GET /complaints/<id>, GET/POST /complaints/<id>/edit (owner student, Pending only), POST /complaints/<id>/delete (owner student while Pending, or admin), POST /complaints/<id>/assign (staff/admin), POST /complaints/<id>/status (staff/admin).
Triage (Module 3): POST /api/triage/suggest with JSON {"text": "..."} returns {"category": str|null, "priority": str|null, "confidence": float}; nulls and 0.0 when the model file is missing. GET /api/stats (staff/admin) returns {"by_category": {...}, "by_status": {...}, "overdue": int}. GET /dashboard (staff/admin) renders Chart.js charts from /api/stats.

## Complaint form (Module 2) and triage script (Module 3)
Form field ids and names: title, description, category, priority. Module 3 provides static/js/triage.js, which listens to the `description` field, calls /api/triage/suggest and prefills `category` and `priority` (the student can override). Module 2's form template includes that script.

## ML (Module 3)
ml/data/complaints.csv, columns text,category,priority. About 300 rows, at least 40 per category, realistic short hostel complaints, mixed phrasing. Priority guide: High = no water or power, leaks, sparks, safety, fire; Medium = Wi-Fi down, mess hygiene, blocked drains; Low = cosmetic, furniture wear, requests.
ml/train.py: two sklearn Pipelines (category, priority), each TfidfVectorizer(ngram_range=(1,2)) + LogisticRegression(max_iter=1000), 80/20 stratified split, random_state=42, saves {"category": pipe, "priority": pipe} to ml/model.joblib with joblib, prints both accuracies.
hostelops/triage/predictor.py: load_model(), suggest(text) -> (category, priority, confidence).
tests/test_triage.py asserts held-out category accuracy >= 0.80.

## Addendum: cross-module decisions (Shubh owns this file; nobody else edits it)

### Endpoint names
The endpoint is the blueprint name plus the view function name. Use these exact view function names so `url_for` and tests agree.

- Auth: `auth.register`, `auth.login`, `auth.logout`
- Complaints: `complaints.index`, `complaints.list_complaints`, `complaints.new_complaint`, `complaints.detail`, `complaints.edit_complaint`, `complaints.delete_complaint`, `complaints.assign_complaint`, `complaints.update_status`
- Triage: `triage.suggest`, `triage.stats`, `triage.dashboard`

### Templates, static files and CSRF
- All templates live in `hostelops/templates/<module>/` (`auth/`, `complaints/`, `triage/`, `errors/`). Only `base.html` sits directly in `hostelops/templates/`.
- All static files live in `hostelops/static/`.
- Child templates extend `base.html` and fill `title`, `content`, and optionally `scripts`.
- `base.html` owns the CSRF meta tag, shared stylesheet link, role-aware navigation, flash messages and shared blocks.
- Navigation uses plain paths so one module can be developed before all blueprints are merged: `/complaints`, `/complaints/new`, `/dashboard`, `/login`, `/register`.
- Navigation: students see Complaints and New Complaint; staff see Complaints and Dashboard; administrators see Complaints and Dashboard; anonymous users see Login and Register. All authenticated users see a POST Logout form.
- Every POST form includes a hidden `csrf_token` input. JavaScript POST requests send the CSRF token in `X-CSRFToken`, read from the meta tag or form token.
- Module 2's create and edit forms retain IDs/names `title`, `description`, `category`, `priority`, and include `<small id="triage-hint"></small>` directly under the description field.
- Dates are displayed as `%d %b %Y %H:%M`.

### Shared UI classes
Module 1 defines these in `hostelops/static/css/style.css`; all modules reuse them:

`container card btn btn-primary btn-danger btn-secondary form-group table badge badge-pending badge-progress badge-resolved badge-overdue badge-high badge-medium badge-low flash flash-success flash-danger flash-info muted grid`

The shared premium SaaS page classes are:

`page-shell page-header page-eyebrow page-title page-description page-actions panel panel-header panel-body stats-grid stat-card stat-label stat-value filter-panel filter-grid complaint-list complaint-card complaint-card-header complaint-card-title complaint-meta complaint-actions form-layout form-card form-section form-sidebar form-help detail-layout detail-main detail-sidebar detail-section activity-timeline activity-item empty-state empty-state-icon`

Do not create competing CSS files or use inline CSS to work around missing shared classes. Report missing shared classes to Shubh.

### Behaviour and permissions
- Passwords are at least 8 characters.
- Public registration always creates role `student`.
- Login redirects to `/complaints` by default. A `next` URL is accepted only when it starts with exactly one slash and is not protocol-relative (for example, reject `//example.com`).
- Flash categories are `success`, `danger`, `info`.
- Students can list and view only their own complaints.
- Staff and administrators can list and view all complaints and use valid status, category and priority filters.
- Only the owner student can edit a complaint, and only while its status is Pending.
- The owner student can delete only a Pending complaint; administrators can delete any complaint; staff cannot delete complaints.
- Only staff and administrators can assign complaints or update their status.
- Assignment targets must exist and have role `staff` or `admin`.
- Setting status to Resolved sets `resolved_at` to `utcnow()`. Moving away from Resolved clears `resolved_at`.
- Overdue means status is Pending or In Progress and age strictly exceeds `OVERDUE_HOURS`. Resolved complaints are never overdue.
- Permission failures return 403 and missing complaints return 404.
- Until all modules are integrated, do not add tests that assume every login redirect is available on every feature branch.

### ML contract (Module 3)
- `ml/data/complaints.csv` is synthetic sample data, not real hostel data. It has columns `text,category,priority`, approximately 300 rows and at least 40 rows per category.
- `ml/train.py` exposes `train(csv_path=DEFAULT_CSV, model_path=DEFAULT_MODEL)`, trains category and priority pipelines using TF-IDF bigrams and LogisticRegression, saves both with joblib, and returns category and priority accuracy.
- Run training from the project root with `python -m ml.train`. Paths are resolved relative to the project root.
- `ml/model.joblib` is generated during Docker build and remains out of Git.
- `hostelops/triage/predictor.py` exposes `load_model(path=None)`, `clear_cache()` and `suggest(text, model_path=None)`. Blank/short text or a missing model returns `(None, None, 0.0)`.
- `POST /api/triage/suggest` requires authentication and accepts JSON `{"text": "..."}`; invalid JSON returns 400, unauthenticated access returns 401.
- `GET /api/stats` is staff/admin only and returns `by_category`, `by_status`, and `overdue`. `GET /dashboard` is staff/admin only.

### Shared test helpers (Module 4)
- `tests/conftest.py` provides `app`, `client`, `runner`, `make_user(role='student', email=None, password='password123', name=None, room_no=None)`, and `login_as(client, user)`.
- Use these shared fixtures instead of defining duplicate module-local factories once the foundation is merged.
