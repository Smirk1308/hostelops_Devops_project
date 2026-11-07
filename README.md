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
| **Shreyansh Jain** | [@Shreyanshj55555](https://github.com/Shreyanshj55555) | **Module 1 (Auth & UI Shell)** | Authentication, role authorization, base UI layout and styling. |

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

$$\text{Shubh (@Smirk1308)} \rightarrow \text{Shivam (@shivam19-debug)} \rightarrow \text{Shashank (@shashankcell)} \rightarrow \text{Shreyansh (@Shreyanshj55555)} \rightarrow \text{Shubh (@Smirk1308)}$$

1. Shubh's PRs are reviewed by Shivam.
2. Shivam's PRs are reviewed by Shashank.
3. Shashank's PRs are reviewed by Shreyansh.
4. Shreyansh's PRs are reviewed by Shubh.
5. Shubh gives final approval on PRs from `staging` to `main`.

---

## Demo Credentials

Run `python scripts/seed.py` to populate initial demo accounts in the database:

| Role | Email | Password | Details |
|---|---|---|---|
| **Admin** | `admin@hostelops.local` | `admin123` | Full system access, user management |
| **Staff** | `staff@hostelops.local` | `staff123` | View all complaints, assign, update status |
| **Student** | `student@hostelops.local` | `student123` | Room A-101; submit and track own complaints |

---

## Local Setup

### 1. Prerequisites
- Python 3.12+ installed
- Git

### 2. Clone and Create Virtual Environment
```bash
git clone https://github.com/Smirk1308/hostelops_Devops_project.git
cd hostelops_Devops_project

python -m venv .venv

# On Linux / macOS:
source .venv/bin/activate

# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
```

### 5. Seed the Database
```bash
python scripts/seed.py
```

### 6. Run the Application
```bash
# Using Flask development server:
flask --app hostelops run --port 8000

# Or using Gunicorn (production / Linux / container):
gunicorn -b 0.0.0.0:8000 "hostelops:create_app()"
```

Access the application in your browser at `http://localhost:8000` and health check at `http://localhost:8000/health`.

---

## Test Commands

Run code linting and the automated test suite:

```bash
# Run Flake8 linter
flake8 .

# Run Pytest suite
pytest

# Run Pytest with verbose output
pytest -v
```

---

## Docker Commands

### Using Docker CLI
```bash
# Build the Docker image
docker build -t hostelops .

# Run the container locally on port 8000
docker run -d --name hostelops-app -p 8000:8000 -e PORT=8000 hostelops

# Verify health endpoint
curl http://localhost:8000/health

# Stop and remove the container
docker stop hostelops-app && docker rm hostelops-app
```

### Using Docker Compose
```bash
# Build and start services in detached mode with persistent storage
docker compose up -d --build

# View container logs
docker compose logs -f

# Stop and remove services
docker compose down
```
