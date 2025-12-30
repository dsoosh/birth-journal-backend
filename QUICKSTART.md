# Quick Start Guide

## Prerequisites
- PostgreSQL installed and running
- Python 3.11+ with venv
- Dependencies installed: `pip install -r requirements-dev.txt`

## Setup

### 1. Create Test Database (one-time)
```sql
CREATE USER midwife_test WITH PASSWORD 'midwife_test_pw';
CREATE DATABASE birth_journal_test OWNER midwife_test;
GRANT ALL PRIVILEGES ON DATABASE birth_journal_test TO midwife_test;
```

### 2. Run Tests
```powershell
$env:DATABASE_URL="postgresql+psycopg://midwife_test:midwife_test_pw@localhost:5432/birth_journal_test"
python -m pytest -q
```

### 3. Start the Backend
```powershell
$env:DATABASE_URL="postgresql+psycopg://midwife_test:midwife_test_pw@localhost:5432/birth_journal_test"
$env:JWT_SECRET="dev-secret-key"
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Open the UI
Open your browser to: **http://localhost:8000**

## Features

### Midwife Workflow
1. Click "Login (Midwife)"
2. Create cases → Get join codes for women
3. View cases in "Cases" tab
4. See events in "Events" tab
5. Check alerts in "Alerts" tab

### Woman Workflow
1. Switch to "Woman" role
2. Enter join code → "Join Case (Woman)"
3. Log events:
   - Labor events (waters breaking, mucus plug, bleeding, etc.)
   - Contractions (start/end)
   - Postpartum check-ins
4. Sync to server
5. View event feed in "Events" tab

## API Endpoints (Full List)

### Auth
- `POST /api/v1/auth/login` - Midwife login (PoC: any username/password)
- `POST /api/v1/cases/join` - Woman joins case with join code

### Cases
- `POST /api/v1/cases` - Midwife creates case
- `GET /api/v1/cases` - Midwife lists cases (pagination supported)
- `GET /api/v1/cases/{case_id}` - Midwife gets case details
- `POST /api/v1/cases/{case_id}/rotate-join-code` - Midwife rotates join code
- `POST /api/v1/cases/{case_id}/close` - Midwife closes case

### Events (Append-only)
- `POST /api/v1/events/sync` - Woman/Midwife syncs events (idempotent by event_id)
- `GET /api/v1/cases/{case_id}/events` - Midwife reads event feed (cursor-based pagination)

### Alerts (Optional)
- `GET /api/v1/alerts` - Midwife alert inbox
- `GET /api/v1/alerts?status=active` - Active alerts only
- `GET /api/v1/cases/{case_id}/alerts` - Alerts for a case
- `POST /api/v1/cases/{case_id}/alerts/{alert_event_id}/ack` - Acknowledge alert
- `POST /api/v1/cases/{case_id}/alerts/{alert_event_id}/resolve` - Resolve alert

### Health
- `GET /api/v1/health` - Health check (includes DB connectivity)

## Notes

- **Auth (PoC):** Simple JWT tokens. PoC accepts any username/password for midwife login.
- **Join codes:** 6-character alphanumeric, case-insensitive. Stored as hashes.
- **Events:** Server derives `track` from `type` (labor/postpartum/meta).
- **Cursors:** Opaque, monotonic `event_seq` for pagination.
- **Offline-tolerant:** Client-side event queuing + idempotent sync ready (implement in client app next).

## File Structure
```
backend/
  app/
    main.py          - FastAPI app + static file serving
    settings.py      - Config from environment
    db.py            - SQLAlchemy engine + session
    models.py        - Case + Event ORM models
    auth.py          - JWT + principal objects
    join_code.py     - Join code generation/hashing
    track.py         - Event type → track derivation
    api/
      router.py      - All endpoints
      schemas.py     - Pydantic schemas
  migrations/        - Alembic migrations

static/
  index.html         - Single-page web UI

tests/
  conftest.py        - pytest fixtures (DB setup)
  test_events_sync.py- Core event pipeline tests
```
