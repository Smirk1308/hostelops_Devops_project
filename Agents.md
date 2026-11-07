# AGENTS.md: HostelOps

## Read first
Before every task, read this file and docs/SPEC.md. SPEC.md defines the exact data models, routes, function names and form field ids. Follow them exactly; do not invent new names or change existing ones. If something is not covered, choose the simplest option and note it in NOTES.md.

## Project
HostelOps is a hostel complaint and maintenance tracking web app built by a team of 4 second-year CSE students for a college Collaborative Development and DevOps mini-project. It is demonstrated at a Project Expo on 21 Nov 2026 to an external examiner, so the app, the CI/CD pipeline, GitHub Actions and Docker must all work live. Residents raise complaints, staff assign and resolve them, admin manages users and sees analytics, and a small ML model suggests category and priority from the complaint text.

## Team and module ownership
- Shubh Sharma (GitHub Smirk1308): repo owner, overseer. Module 4: test configuration, Docker, CI/CD, deployment.
- Shivam Choudhary (shivam19-debug): Module 3: triage ML, overdue logic, analytics dashboard.
- Shashank Lodhi (shashankcell): Module 2: complaint management.
- Shreyansh Jain (Shreyanshj55555): Module 1: auth, roles, UI shell; README polish.
Branches: main, staging, feature/devops, feature/triage, feature/complaints, feature/auth.
Changes reach staging only through pull requests. Review ring: Shubh's PRs are reviewed by Shivam, Shivam's by Shashank, Shashank's by Shreyansh, Shreyansh's by Shubh. Shubh gives final approval on staging to main.

## Hard constraints
- Python only (Flask). Frontend is HTML, CSS and JavaScript via Jinja templates. No Node.js, no React, no frontend build step. Chart.js may be loaded from a CDN script tag.
- Database: SQLite through SQLAlchemy.
- No external APIs, no scraping, no paid services, no real-world data. The ML training set is a synthetic CSV documented as sample data.
- Runs locally with one command and deploys through Docker and Render.
- Code must be simple and readable with comments on non-obvious parts. The students must be able to explain every file.

## Structure
Flask app factory, one blueprint per module:
- hostelops/auth/ (Module 1, also templates/base.html and static/css/style.css)
- hostelops/complaints/ (Module 2)
- hostelops/triage/ and ml/ (Module 3)
- tests/test_auth.py, test_complaints.py, test_triage.py, test_health.py: each owner writes the tests for their own module
- Module 4 owns pytest.ini, tests/conftest.py, flake8 config, Dockerfile, docker-compose.yml, .github/

## DevOps
ci.yml on push and pull_request: install, flake8, pytest, build the image, run the container, curl /health. cd.yml: push to staging triggers a Render deploy hook (secret RENDER_DEPLOY_HOOK_URL); push to main builds and pushes the image to GitHub Container Registry. Steps with a missing secret must skip, not fail. Pin all dependency versions. Conventional commits (feat:, fix:, test:, ci:, docs:).

## How the agent should behave
- Do one task at a time. Edit only the files of the module you were asked to work on. If another module needs a change, say so instead of editing it.
- Before finishing, re-read the task and SPEC.md and check every point. Run flake8 and pytest and fix failures.
- Make small, logical local commits. Never push, deploy or add real secrets.
- Do not ask questions unless blocked. State assumptions at the end.