# HostelOps

HostelOps is a hostel complaint and maintenance tracking web application built by a team of four second-year CSE students for a college Collaborative Development and DevOps mini-project.

Residents raise complaints across categories (Water, Electricity, Wi-Fi, Mess, Cleanliness, Furniture, Other). Hostel staff assign and resolve them, administrators oversee users and analytics, a machine learning triage model suggests complaint categories and priorities from text, and complaints exceeding a configurable deadline are flagged as overdue.

---

## Team and Module Ownership

| Name | GitHub | Module | Responsibilities |
|---|---|---|---|
| **Shubh Sharma** | [@Smirk1308](https://github.com/Smirk1308) | **Module 4 (DevOps & Overseer)** | Project lead, test configuration, Docker, CI/CD pipelines, deployment. |
| **Shivam Choudhary** | [@shivam19-debug](https://github.com/shivam19-debug) | **Module 3 (Triage & Analytics)** | ML triage model, overdue complaint logic, analytics dashboard. |
| **Shashank Lodhi** | [@shashankcell](https://github.com/shashankcell) | **Module 2 (Complaints)** | Complaint lifecycle: creation, filtering, editing, status & assignment. |
| **Shreyansh Jain** | [@Shreyanshj55555-stack](https://github.com/Shreyanshj55555-stack) | **Module 1 (Auth & UI Shell)** | Authentication, role authorization, base UI layout and styling. |

---

## Branching and Review Workflow

- **Primary Branches**: `main` (production-ready) and `staging` (pre-production integration).
- **Feature Branches**:
  - `feature/devops` (Module 4)
  - `feature/triage` (Module 3)
  - `feature/complaints` (Module 2)
  - `feature/auth` (Module 1)
- **Integration Rule**: Changes reach `staging` exclusively via pull requests. Direct commits to `main` and `staging` are prohibited.

### Review Ring

To ensure thorough cross-module peer reviews, pull requests follow a circular review ring:

$$\text{Shubh (@Smirk1308)} \rightarrow \text{Shivam (@shivam19-debug)} \rightarrow \text{Shashank (@shashankcell)} \rightarrow \text{Shreyansh (@Shreyanshj55555-stack)} \rightarrow \text{Shubh (@Smirk1308)}$$

1. Shubh's PRs are reviewed by Shivam.
2. Shivam's PRs are reviewed by Shashank.
3. Shashank's PRs are reviewed by Shreyansh.
4. Shreyansh's PRs are reviewed by Shubh.
5. Shubh gives final approval on PRs from `staging` to `main`.

---

## Demo Credentials

The seed script creates these local demonstration accounts when they do not
already exist:

| Role | Email |
|---|---|
| **Admin** | `admin@hostelops.local` |
| **Staff** | `staff@hostelops.local` |
| **Student** | `student@hostelops.local` |

Passwords are configured locally through `.env`. Demo seeding requires an
explicit opt-in and three strong passwords; never reuse demo passwords in
production or use demo accounts for production access. Do not commit `.env`.

---

## Local Setup

### 1. Prerequisites
- Python 3.12+ installed
- Git

### 2. Clone the Repository and Create a Virtual Environment
```bash
git clone https://github.com/Smirk1308/hostelops_Devops_project.git
cd hostelops_Devops_project
```

Create the virtual environment:

**Windows PowerShell:**
```powershell
py -m venv .venv
```

**Linux / macOS:**
```bash
python3 -m venv .venv
```

### 3. Install Dependencies

**Windows PowerShell (works without activating the environment):**
```powershell
.\\.venv\\Scripts\\python.exe -m pip install --upgrade pip
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
```

**Linux / macOS:**
```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-dev.txt
```

### 4. Configure Environment

**Windows PowerShell:**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Edit `.env` and set `HOSTELOPS_ENABLE_DEMO_SEED=1` plus strong values for
`HOSTELOPS_SEED_ADMIN_PASSWORD`, `HOSTELOPS_SEED_STAFF_PASSWORD`, and
`HOSTELOPS_SEED_STUDENT_PASSWORD`. Each password must be at least 12 characters
and include at least three of lowercase letters, uppercase letters, digits,
and symbols. Keep these values private and never use them as production
credentials.

### 5. Train the Machine Learning Model

Train the complaint categorization and priority triage model:

**Windows PowerShell:**
```powershell
.\.venv\Scripts\python.exe -m ml.train
```

**Linux / macOS:**
```bash
python -m ml.train
```

### 6. Seed the Database

The script loads `.env` from the repository root and preserves values already
provided by the shell. Run it only after completing the configuration above.

**Windows PowerShell:**
```powershell
.\.venv\Scripts\python.exe scripts/seed.py
```

**Linux / macOS:**
```bash
python scripts/seed.py
```

Existing demo-account passwords are preserved by default. To intentionally
rotate only the three demo accounts to the passwords configured in `.env`, set
`HOSTELOPS_ROTATE_DEMO_PASSWORDS=1` in `.env`, run the seed command again, then
change it back to `0`. The seed script rejects environments marked as
production.

### 7. Run the Application
```bash
# Using Flask development server:
flask --app hostelops run --port 8000

# Or using Gunicorn (production / Linux / container):
gunicorn -b 0.0.0.0:8000 "hostelops:create_app()"
```

Access the application in your browser at `http://localhost:8000` and health check at `http://localhost:8000/health`.

---

## Test Commands

Run linting and tests from the project root.

**Windows PowerShell:**
```powershell
.\\.venv\\Scripts\\python.exe -m flake8 .
.\\.venv\\Scripts\\python.exe -m pytest
```

**Linux / macOS (with the virtual environment activated):**
```bash
python -m flake8 .
python -m pytest
```

---

## Docker Commands

### Using Docker CLI
```bash
# Build the Docker image
docker build -t hostelops .

# Run the container locally on port 8000
docker run -d --name hostelops-app --env-file .env -p 8000:8000 -e PORT=8000 hostelops

# Verify health endpoint
curl http://localhost:8000/health

# Stop and remove the container
docker stop hostelops-app && docker rm hostelops-app
```

### Using Docker Compose
Create the environment file first. PowerShell: `Copy-Item .env.example .env` (Linux/macOS: `cp .env.example .env`).

```bash
# Build and start services in detached mode with persistent storage
docker compose up -d --build

# View container logs
docker compose logs -f

# Stop and remove services
docker compose down
```

---

## Production Configuration & Security

When deployed to production (e.g. Render, or with `HOSTELOPS_ENV=production` / `RENDER=true`), HostelOps activates strict security controls:

1. **Secret Key Validation**: `SECRET_KEY` must be explicitly configured, at least 16 characters long, and distinct from default development keys (`dev`, `password`, `test-secret-key`, etc.). Startup halts with an error if an insecure or missing key is detected.
2. **Hardened Session Cookies**: `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, and `SESSION_COOKIE_SAMESITE = 'Lax'`.
3. **Debug Mode**: Flask debug mode is strictly disabled (`DEBUG = False`).
4. **CSRF Protection**: Flask-WTF CSRF protection is active across all endpoints and AJAX requests.

### Database Persistence & PostgreSQL

HostelOps supports both local SQLite and PostgreSQL:
- **Local Development**: Uses SQLite stored in the Flask instance directory (`instance/hostelops.db`). Docker Compose mounts `/app/instance` as a persistent named volume.
- **Production Persistence**: On cloud platforms like Render, SQLite without a persistent disk loses state across redeployments and restarts. For production, either:
  - Attach a **Render Persistent Disk** mounted at `/app/instance`, or
  - Configure a managed **Render PostgreSQL** database and provide the connection URI as `DATABASE_URL`. HostelOps automatically normalizes legacy `postgres://` URLs to SQLAlchemy's `postgresql://` dialect via `psycopg2-binary`.
- **Note on Migrations**: `db.create_all()` initializes tables on clean deployments, but is not a database migration framework. Future structural schema changes should use Alembic or manual DDL migrations.

---

## Deployment & CI/CD Setup (Render & GitHub Actions)

### Continuous Integration (CI)
Every push and pull request to `staging` and `main` triggers `.github/workflows/ci.yml`:
1. Installs pinned dependencies (`requirements.txt` and `requirements-dev.txt`).
2. Runs static linting with `flake8`.
3. Executes all 158 automated unit and integration tests with `pytest`.
4. Builds the container image and trains the ML model inside Docker.
5. Boots the container and validates the `/health` endpoint.

### Continuous Deployment (CD)
On push to `staging`, `.github/workflows/cd.yml` automates deployment to Render:
1. Validates that deployment secrets exist (fails fast if either secret is missing).
2. Triggers deployment via the Render Deploy Hook.
3. Polls `${HOSTELOPS_STAGING_URL}/health` (up to 5 minutes with 10s intervals) to confirm the service is healthy before passing.

#### Configuring Render Deployment Secrets in GitHub
To enable staging CD:
1. In your **Render Dashboard**, navigate to your HostelOps Web Service -> **Settings** -> **Deploy Hook**. Copy the URL.
2. In your **GitHub Repository**, go to **Settings** -> **Secrets and variables** -> **Actions** -> **Repository secrets**.
3. Add the following secrets:
   - `RENDER_DEPLOY_HOOK_URL`: Your Render Deploy Hook URL.
   - `HOSTELOPS_STAGING_URL`: Your full Render service URL (e.g., `https://hostelops-staging.onrender.com`).

*(Note: In PR #7, project lead Shubh Sharma approved a documented review exception to bypass pending peer review to finalize integration readiness.)*
