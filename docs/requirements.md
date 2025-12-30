# docs/requirements.md

## Functional requirements (PoC)

### 1) Case lifecycle
- Create a **case** in midwife UI (maps identity -> case).
- Woman app uses **pseudonymous case code / QR** to join.
- Case can be **active labor**, **postpartum active**, or both.
- Case can be closed/archived by midwife.

### 2) Labor track
#### 2.1 Contraction logging (woman)
- Start contraction / End contraction (single-button + optional end auto after X seconds).
- Display: last contraction duration, interval, simple trend.
- Offline-first: events queued and synced later.

#### 2.2 Labor events (woman)
Allow logging of notable events (quick list + optional notes):
- waters breaking (time, color/odor optional)
- bleeding (light/medium/heavy)
- reduced fetal movement (flag only)
- belly lowering
- nausea/vomiting
- urge to push
- headache/visual changes
- fever/chills
- other (free text)

#### 2.3 Milestones (system)
- Compute based on contraction events:
  - **5-1-1**: contractions ~5 min apart, lasting ~1 min, sustained ~1 hour
  - **3-1-1**: ~3 min apart, ~1 min duration, sustained ~1 hour
  - **Regression**: previously regular pattern becomes less frequent for sustained window
  - **Abnormal gap**: no contractions logged for long gap after established pattern
- Milestone triggers create **alerts** visible to midwife; optionally show a subtle on-device banner to woman.

#### 2.4 Alerts philosophy
- No per-contraction notifications.
- Alerts only for milestones and high-signal events (e.g., heavy bleeding).

### 3) Postpartum track
#### 3.1 Woman check-ins (minimal)
- Scheduled or prompted check-ins (e.g., daily): quick yes/no + severity:
  - heavy bleeding / clots
  - fever
  - severe headache/vision issues
  - wound/pain concerns
  - mood red flags (optional PoC)
  - breastfeeding issues (optional PoC)
- Free text optional, default off.

#### 3.2 Midwife visits workflow
- Midwife can create visit tasks: planned date, status (planned/done), notes.
- Midwife can record observations as events.

### 4) Midwife dashboard
- List of active cases with:
  - last activity time
  - active alerts count
  - labor/postpartum status
- Case details:
  - timeline (events + derived milestones)
  - current contraction stats (rolling window)
  - postpartum check-ins
  - notes
- Alert inbox:
  - filter by severity, time, status (new/acknowledged/resolved)

### 5) Roles & access
- Woman app: case-scoped access only.
- Midwife app: access to assigned cases + identity mapping.

### 6) Non-functional requirements
- GDPR: data minimization, pseudonymous IDs in woman app.
- Deterministic rules, versioned.
- Auditability: all alerts and acknowledgements are events.
- Offline tolerant: local queue + idempotent sync.

## Out of scope (PoC)
- Device pairing (KTG integration, contraction sensors)
- Advanced ML predictions
- Chat/messaging (unless strictly needed for pilot logistics)
