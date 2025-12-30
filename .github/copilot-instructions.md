# Copilot Instructions – Położne

You are working on the **Położne** project, a PoC for labor/postpartum monitoring with midwife oversight.

## Project Structure (3 repos in workspace)
- **`birth-journal-backend/`** — FastAPI backend + docs (this is source of truth)
- **`birth-journal-midwife-app/`** — Flutter mobile app (midwife's mobile tools)
- **`birth-journal-patient-app/`** — Flutter mobile app (pregnant person's offline-first app)

## Core Principles (non-negotiable)
Before making suggestions or code changes, **always read**:
- `docs/context.md` — objectives, users, product boundaries
- `docs/architecture.md` — event-based model, sync strategy, repo layout
- `docs/api.md` — REST endpoints, event schemas (authoritative source for contracts)
- `docs/privacy-security.md` — GDPR-first data handling, access control, audit trails

**Design rules:**
- Event-based model only (append-only `events` table with `event_seq` identity column)
- Server-authoritative: backend **overrides** client-provided `track` using `derive_track(type)` in `backend/app/track.py`
- Deterministic rules, no black-box AI
- Offline-tolerant clients: idempotent sync by `event_id` (UUID), opaque `cursor` (backed by `event_seq`)
- Safety and clarity over features

## Backend (FastAPI + PostgreSQL)

### Commands
```powershell
# Setup (one-time)
CREATE USER midwife_test WITH PASSWORD 'midwife_test_pw';
CREATE DATABASE midwife_support_test OWNER midwife_test;

# Run tests
$env:DATABASE_URL="postgresql+psycopg://midwife_test:midwife_test_pw@localhost:5432/midwife_support_test"
python -m pytest -q

# Start dev server
$env:DATABASE_URL="postgresql+psycopg://..."
$env:JWT_SECRET="dev-secret-key"
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Migrations (Alembic)
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Key files
- `backend/app/main.py` — FastAPI app + CORS + static file serving
- `backend/app/api/router.py` — all REST endpoints (auth, cases, events, alerts)
- `backend/app/api/schemas.py` — Pydantic schemas for requests/responses
- `backend/app/models.py` — SQLAlchemy ORM (Case, Event, Midwife)
- `backend/app/track.py` — `derive_track(event_type)` maps event types → tracks (`labor|postpartum|meta`)
- `backend/app/auth.py` — JWT minting + principals (`require_midwife`, `require_case`)
- `backend/app/join_code.py` — 6-char alphanumeric join code generation + bcrypt hashing
- `backend/migrations/versions/` — Alembic migrations (append-only event store)

### Data model patterns
- **Events table:** `event_id` (PK, UUID), `case_id` (FK), `event_seq` (identity, for cursor), `type`, `ts` (client), `server_ts` (server), `track`, `source`, `payload_v`, `payload` (JSONB)
- **Cursor pagination:** Opaque cursors are stringified `event_seq` integers; use `_parse_cursor()` helper in router
- **Idempotency:** Sync endpoint uses `INSERT ... ON CONFLICT (event_id) DO NOTHING` (see `test_sync_idempotent_event_id`)
- **Track derivation:** Client-provided `track` is **ignored**; server calls `derive_track(type)` before insert (see `test_track_is_overridden_when_wrong`)

### Event types reference (from `docs/api.md`)
- **Labor:** `contraction_start`, `contraction_end`, `labor_event` (waters_breaking, mucus_plug, bleeding), `set_labor_active`
- **Postpartum:** `postpartum_checkin`, `set_postpartum_active`
- **Meta:** `alert_*`, `note`, `visit_task`

### Auth scopes
- **Midwife JWT:** `POST /auth/login` → role=midwife, can access all assigned cases
- **Woman token:** `POST /cases/join` → case-scoped JWT, can only read/write events for one `case_id` (enforced in sync endpoint, see `test_auth_scope_woman_cannot_write_other_case`)

## Flutter Apps (Mobile + Web)

### Commands (both mobile apps)
```powershell
flutter pub get
flutter run -d android --dart-define API_BASE_URL=http://10.0.2.2:8000/api/v1  # Android emulator
flutter run -d chrome --dart-define API_BASE_URL=http://localhost:8000/api/v1  # Web debugging
flutter build apk --dart-define API_BASE_URL=http://...                        # Production APK
flutter test
```

### Contracts (strict, from docs)
- **Event sync:** Use `POST /events/sync` with opaque `cursor` (never timestamps)
- **Event envelope:** Must include `event_id` (UUID), `case_id`, `type`, `ts` (ISO-8601 UTC), `payload_v: 1`
- **Track field:** Client can omit or send wrong value; server **always overrides** using backend logic
- **Offline queue:** Store events locally (Hive/sqflite), sync with retry on reconnect, rely on server idempotency
- **No streaming:** Use cursor-based pagination (`/cases/{case_id}/events`) for event feeds

### Woman app (`birth-journal-patient-app/`)
- **Single-profile:** One case per device (join code shared in person)
- **No alerts:** Woman sees only her own event log; midwife monitors
- Offline queue → sync when online
- Labor mode: quick capture (1-2 taps), contraction tracking
- Postpartum mode: check-in forms

### Midwife mobile (`birth-journal-midwife-app/`)
- **Multi-case:** Midwife manages many active cases
- Login screen implemented (`lib/screens/login_screen.dart`)
- Next: cases list, event feeds, alerts inbox, create case/join code
- Push notifications (Firebase Cloud Messaging / APNs) for critical alerts

## Testing patterns
- See `tests/conftest.py` for test client setup
- See `tests/test_events_sync.py` for sync idempotency, cursor, track override, auth scope examples
- Backend tests require `DATABASE_URL` env var (Postgres only, uses JSONB + identity columns)
- Use `_auth(client, token)` helper for Authorization headers

## Common patterns
- **Case creation:** Midwife calls `POST /cases` → returns `case_id` + `join_code` (6-char, hashed with bcrypt)
- **Join flow:** Woman calls `POST /cases/join` with `join_code` → receives case-scoped JWT
- **Event sync:** Client sends batch with `cursor` + `events[]` → server responds with `accepted_event_ids`, `rejected[]`, `server_cursor`, `new_events[]`
- **Pagination:** All list endpoints use `cursor` (opaque) + `limit` (default 50, max 200)
- **Deterministic flags:** `labor_active`, `postpartum_active` computed from latest `set_labor_active`/`set_postpartum_active` events (not stored in case table)

## Privacy & Security (GDPR-first)
- **Data separation:** `device_id` ≠ `case_id` ≠ real identity (identity mapping in separate table, midwife-only)
- **Join codes:** Short-lived, bcrypt-hashed, rate-limited, rotatable (`POST /cases/{case_id}/rotate-join-code`)
- **Audit trail:** All actions create events (append-only)
- **No PII in logs:** Use structured logging, no email/name/address in log output
- **TLS everywhere:** Never commit secrets (use env vars)

## When adding features
1. Check if event type exists in `docs/api.md` (if not, propose new type in payload spec)
2. Update `derive_track()` in `backend/app/track.py` if new type needs non-default track
3. Add Pydantic schema to `backend/app/api/schemas.py`
4. Write integration test in `tests/` (follow idempotency + cursor patterns)
5. Keep it deterministic: no random AI predictions, explainable rules only
