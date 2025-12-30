
# docs/context.md

## Położne — PoC context (source of truth)

### Objective
Build a safe, simple, cross-platform PoC that supports:
- **Labor monitoring** (contractions, milestones, notable events)
- **Postpartum monitoring** (checks, symptoms, visit workflow)
in **parallel tracks**, with **minimal attention** required during labor.

### Users
- **Woman (patient-facing, phone app):** quick capture, low cognitive load, offline-tolerant.
- **Midwife (responsive web view on phone/desktop):** overview of active cases, meaningful alerts, history, minimal noise.

### Interfaces (PoC)
- **Pregnant person's phone app (Flutter Mobile):**
  - **Labor mode:** quick signal of pre-birth events (waters breaking, mucus plug, bleeding, etc.) and a dedicated contractions view for monitoring.
  - **Postpartum mode:** after delivery, log post-partum events and check-ins.
  - Offline-tolerant: SQLite queue for events; sync when reconnected.
  - **Pairing:** In-person only (scans QR code or manually enters join code from midwife).
  - **No alerts:** woman sees only her own event log; midwife monitors and alerts via push notification.
- **Midwife tools (Flutter Web + Mobile app):**
  - **Web dashboard:** list of active cases, event feeds, alerts inbox, case history.
  - **Midwife mobile app:** push notifications for alerts + case actions (acknowledge, resolve, close).
  - Case creation + join code generation (shared in person with woman).
  - Push notifications to both web + mobile to avoid missed alerts.

### Core principles (non-negotiable)
- Safety and clarity over features.
- Few meaningful alerts; avoid notification fatigue.
- Explainable rules > black-box automation.
- Event-based data (timestamped observations), not streams.
- PoC pragmatism: boring tech, fast iteration, low ops.

### Tech constraints
- Pregnant person's app: Flutter (Android/iOS)
- Midwife tools: Flutter Web (browser) + Flutter Mobile (iOS/Android)
- Backend: FastAPI (Python)
- DB: PostgreSQL (single source of truth)
- Server-authoritative, offline-tolerant clients
- Push notifications for midwife tools (Firebase Cloud Messaging / APNs)
- Polling or scoped websockets for web dashboard

### Product boundaries (PoC)
We do:
- Manual + semi-automatic contraction tracking
- Postpartum checks + midwife visit workflow
- Midwife dashboard (active cases, alerts, history)
- Ability to log other events (waters breaking, bleeding, etc.)
- In-person pairing (QR code or join code shared face-to-face)

Optional:
- Milestones (e.g., 5-1-1, 3-1-1, regression, abnormal gaps)
- Simple pattern detection (frequency/regularity trends)

We do NOT (PoC):
- Remote pairing (no invite links, no phone number verification, no QR scanning across networks)
- Continuous monitoring, streaming, heavy real-time
- Medical decisioning or diagnosis
- "AI" recommendations that override clinician judgment

### Data model mindset
Everything is a **timestamped event** attached to a **case**.
- Contraction events
- Symptom/events
- Milestone triggers (derived events)
- Midwife notes/actions
- Postpartum check-ins

### Success criteria (PoC)
- Woman can log contractions/events with **1–2 taps**.
- Midwife sees **only** actionable alerts (milestones, abnormal patterns).
- Backend rules are deterministic, debuggable, testable.
- System works with intermittent connectivity (no data loss).
