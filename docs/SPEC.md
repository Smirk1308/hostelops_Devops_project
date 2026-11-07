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