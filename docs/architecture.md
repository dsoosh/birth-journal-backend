# docs/architecture.md

## Architecture overview (PoC)

### Components
- **Pregnant person's app (Flutter Mobile; separate repo: `birth-journal-patient-app`)**
  - Offline event queue (SQLite/Hive)
  - Labor event logging (waters breaking, mucus plug, bleeding, etc.) + contraction tracking
  - Postpartum check-in form
  - Sync via REST when online
  - In-person pairing: scans QR code or manually enters join code from midwife
  - **Single-profile:** logged in as one case only
- **Midwife tools (Flutter Web + Mobile; separate repo: `birth-journal-midwife-app`)**
  - **Web dashboard:** case list, event feeds, alerts inbox, case history (responsive HTML/JS or Flutter Web)
  - **Mobile app:** push notifications for alerts + case management actions
  - Push notifications to both web + mobile platforms for redundancy (avoid missed critical alerts)
  - **Multi-case:** midwife can manage many active cases
  - Case setup: create case in person, generate join code for woman to use
- **FastAPI Backend (this repo: `birth-journal-backend`)**
  - REST API for both clients
  - Rule engine (deterministic, versioned)
  - Auth + access control (case-scoped tokens for woman, midwife session auth)
  - Push notification service (Firebase Cloud Messaging, APNs)
- **PostgreSQL**
  - Event store tables (append-first)
  - Derived views/materialized summaries optional

### Data model
Event-based:
- `observation_event` (woman-entered and midwife-entered)
- `derived_event` (milestones/alerts produced by backend)
- `action_event` (acknowledge, resolve, close case)

Do not stream. Compute summaries on read or via background job.

### Sync strategy (offline tolerant)
- Client generates `event_id` (UUID) and sends batch to `/events:sync`.
- Server is idempotent:
  - ignore duplicates by `event_id`
- Server responds with:
  - accepted ids
  - latest server cursor / updated_at watermark
  - new derived events for the case

### Rule engine (PoC)
- Stateless functions operating on a case’s recent events (rolling windows).
- Deterministic outputs with:
  - rule version
  - inputs window
  - derived_event payload

### Repositories (PoC)
- **`birth-journal-backend`** (this repo): Backend only
  - `backend/` – FastAPI app, ORM models, migrations, API endpoints
  - `web/` – Midwife dashboard (Flutter Web or vanilla JS/CSS SPA)
  - `mobile/` – Midwife mobile app (Flutter, iOS + Android)
  - `tests/` – Backend integration tests
  - `docs/` – Shared API, glossary, architecture, privacy docs
- **`birth-journal-patient-app`** (separate repo): Pregnant person's mobile app only
- **`birth-journal-midwife-app`** (separate repo): Midwife's mobile app only
  - Flutter project for iOS + Android
  - Independent release cycle
  - Single-profile (one case per device)

### Deployment (PoC)
- Single backend service + single Postgres.
- Containerized (Docker).
- Managed Postgres preferred.
- Simple CI:
  - lint
  - unit tests for rules
  - API contract checks (schemas)
- Mobile app: distributed via App Store / Play Store (with PoC builds on TestFlight / Google Play Console)

### Observability
- Structured logs (no PII).
- Basic metrics: request counts, latency, error rate.
- Admin endpoint for health checks.

### Scaling assumptions (PoC)
- Low volume, bursts during labor.
- Focus: reliability + correctness over throughput.
