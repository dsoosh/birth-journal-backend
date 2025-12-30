# Glossary

## Core Concepts

### Case
A **case** is a single pregnancy/labor/postpartum journey between a midwife and one woman.

- **Properties**: `case_id` (UUID), `status` (active/closed), `created_at`, `closed_at`
- **Lifecycle**: Created by midwife → Woman joins via join code → Events logged → Case closed by midwife
- **State flags**: `labor_active`, `postpartum_active` (derived from latest toggle events)
- **Scope boundary**: Woman token is scoped to one case; midwife token can access multiple assigned cases

**Example use**:
- Midwife creates case for Jane Doe → generates join code
- Jane joins case with code on her phone
- Both log events to the same `case_id`
- Midwife closes case after delivery + postpartum period

---

### Event
An **event** is an immutable, timestamped record of something that happened in a case.

**Properties**:
- `event_id` (UUID, client-generated)
- `case_id` (which case this belongs to)
- `type` (string; e.g., `labor_event`, `contraction_start`, `postpartum_checkin`)
- `ts` (client-provided timestamp; when woman/midwife experienced the event)
- `server_ts` (server-generated timestamp; when server received it)
- `track` (derived by server from `type`: labor / postpartum / meta)
- `source` (who logged it: woman / midwife / system)
- `payload_v` (schema version for the payload; currently 1)
- `payload` (event-specific data as JSON)

**Guarantees**:
- Append-only (never deleted or modified)
- Idempotent by `event_id` (same ID sent twice → stored once)
- Auditable (full history preserved)

**Example events**:
```json
{
  "event_id": "uuid",
  "case_id": "uuid",
  "type": "labor_event",
  "ts": "2025-12-29T10:30:00Z",
  "track": "labor",
  "source": "woman",
  "payload": { "kind": "waters_breaking", "severity": "high" }
}

{
  "event_id": "uuid",
  "case_id": "uuid",
  "type": "postpartum_checkin",
  "ts": "2025-12-30T14:00:00Z",
  "track": "postpartum",
  "source": "woman",
  "payload": { "items": { "bleeding": "moderate", "fever": "no", ... } }
}
```

---

### Alert
An **alert** is a derived event that signals something requiring midwife attention.

**Lifecycle**:
1. Server-side rule engine processes case events
2. If rule fires (e.g., 5-1-1 milestone), creates `alert_triggered` event
3. Midwife sees alert in `/alerts` inbox
4. Midwife acknowledges with `alert_ack` event (review only; doesn't resolve)
5. Midwife resolves with `alert_resolve` event (marks as handled)

**Properties**:
- `type`: Always one of `alert_triggered`, `alert_ack`, `alert_resolve`
- `payload.alert_code` (if triggered): e.g., `MILESTONE_511`, `HEAVY_BLEEDING`, `REGRESSION`
- `payload.severity` (if triggered): `info` / `warning` / `urgent`
- `payload.explain` (if triggered): Reason (rule version, window, summary)

**Active alerts** = `alert_triggered` events where there is no corresponding `alert_resolve` (check by `alert_event_id`).

**Ack vs Resolve**:
- `alert_ack` = "I saw this; checking now"
- `alert_resolve` = "Issue handled; stop showing this alert"

**Example**:
```json
{
  "type": "alert_triggered",
  "payload": {
    "alert_code": "MILESTONE_511",
    "severity": "warning",
    "explain": {
      "rule_version": "ruleset-0.1",
      "window_minutes": 60,
      "summary": "5 contractions in 1 hour; heading towards transition?"
    }
  }
}
```

---

### Track
A **track** is a category that groups related events.

**Valid tracks**:
- `labor`: Contractions, labor events (waters breaking, mucus plug, etc.), labor toggle events
- `postpartum`: Postpartum check-ins, postpartum toggle events
- `meta`: Notes, visit tasks, alerts, system events

**Derivation**: Server auto-derives `track` from `event.type` using deterministic rules (see `backend/app/track.py`). Client-provided `track` is ignored.

**Why?** Prevents client drift; server is source of truth for logical grouping.

---

### Join Code
A **join code** is a short, case-specific, human-readable code that a woman uses to join a case.

**Properties**:
- Format: 6 uppercase alphanumeric characters (e.g., `ABCD12`)
- Case-insensitive input; normalized to uppercase
- Only displayed once (at case creation); not stored in plaintext
- Stored as SHA256 hash in DB
- Short-lived; can be rotated by midwife anytime
- Woman enters code → server hashes it → matches DB hash

**Example flow**:
1. Midwife creates case → server generates join code `ABCD12`
2. Midwife shares code with woman (SMS, in-person, etc.)
3. Woman enters `abcd12` (or `ABCD12`) on her phone
4. App hashes it → matches DB hash → returns case-scoped JWT
5. Woman is now authenticated to sync events for that case

---

### Cursor
A **cursor** is an opaque, monotonic continuation token for pagination.

**Properties**:
- Opaque to client (implementation detail: currently the `event_seq` BIGINT)
- Monotonic (always increases; safe for cursor-based pagination)
- Server-issued in responses
- Client sends back on next request for "give me everything after this point"

**Why not timestamps?**
- Clients may have skewed clocks
- Multiple events can occur at same millisecond
- Server sequence is authoritative

**Example flow**:
```
1. Woman syncs: cursor=null → gets events seq 1-10, server_cursor="10"
2. Woman syncs again: cursor="10" → gets events seq 11-20, server_cursor="20"
3. Server response: next_cursor="20" (opaque; client persists it locally)
```

---

### Payload
A **payload** is the event-specific data stored as JSON in the `payload` column.

**Common payloads**:

**labor_event**:
```json
{
  "kind": "waters_breaking | mucus_plug | bleeding | reduced_fetal_movement | ...",
  "severity": "low | medium | high",
  "note": "optional free text"
}
```

**contraction_end**:
```json
{ "duration_s": 62 }
```

**postpartum_checkin**:
```json
{
  "items": {
    "bleeding": "none | light | moderate | heavy",
    "fever": "no | yes",
    "headache_vision": "no | yes",
    "pain": "none | mild | moderate | severe"
  },
  "note": "optional"
}
```

**note** (midwife):
```json
{ "text": "free text observation" }
```

**visit_task** (midwife):
```json
{
  "due_date": "YYYY-MM-DD",
  "status": "planned | done",
  "note": "optional"
}
```

**set_labor_active** / **set_postpartum_active** (midwife toggle):
```json
{ "active": true }
```

---

### Source
A **source** is who logged the event.

**Valid sources**:
- `woman`: Woman on her phone app logged it
- `midwife`: Midwife on web/app logged it (e.g., notes, visit tasks, ack/resolve)
- `system`: Backend auto-generated (alerts, derived events)

---

### Payload Version (`payload_v`)
A **payload version** is a schema version for the event payload.

**Purpose**: Forward compatibility. If payload schema changes, clients can distinguish old/new payloads.

**Current**: Always `1`. Defaults to `1` if omitted.

**Future use**: If labor_event payload gains a new field, payload_v could be incremented; backend logic can handle both v1 and v2.

---

### Sync
**Sync** is the primary operation for offline-tolerant event propagation.

**POST /events/sync request**:
```json
{
  "client_time": "ISO-8601 (optional; for clock skew debugging)",
  "cursor": "opaque-or-null (resume after this point)",
  "events": [ { ...event envelopes... } ]
}
```

**Response**:
```json
{
  "accepted_event_ids": [ "uuid1", "uuid2" ],
  "rejected": [ { "event_id": "uuid", "reason": "..." } ],
  "server_cursor": "monotonic (client persists this)",
  "new_events": [ { ...events server generated since cursor... } ]
}
```

**Guarantees**:
- Idempotent: Same sync payload twice → same response, no duplicates
- Atomic: All events in request fail together or succeed together (within one sync)
- Offline-tolerant: Client queues events locally → syncs when online

---

### Labor Active / Postpartum Active
**labor_active** and **postpartum_active** are boolean case state flags.

**Definition**:
- `labor_active = true` if there is a `set_labor_active` event with `payload.active = true` and it's the latest one for the case (case not closed)
- `postpartum_active = true` if there is a `set_postpartum_active` event with `payload.active = true` and it's the latest one
- Both forced to `false` if case status is `closed`

**Midwife usage**: Quick visual indicator on case summary (list view). Useful for filtering active labor/postpartum cases.

**Implementation**: Derived on read; no separate table. Server recomputes from latest toggle events.

---

### Deterministic Rules
**Deterministic rules** are server-side logic that produces the same output given the same input.

**Contrast with "black-box AI"**: Rules are explicit, testable, and auditable.

**Examples**:
- `event_type → track` mapping (e.g., `labor_event` always maps to `labor`)
- `5-1-1 milestone`: 5+ contractions in 1 hour → trigger `MILESTONE_511` alert
- Case state derivation: Last `set_labor_active` event determines flag

**Rule versioning**: Each derived event includes `rule_version` (e.g., `ruleset-0.1`) so past alerts can be audited.

---

### Offline-Tolerant
The system is designed to work with intermittent connectivity.

**Client-side**:
- Event queue stored locally (SQLite/Hive)
- User logs events even if offline
- Sync when online (batch + idempotent)

**Server-side**:
- Sync endpoint accepts batches
- Idempotent by `event_id`
- Returns cursor for resumption

**Result**: No data loss; no double-logging if sync fails.

---

### Milestones (Optional in PoC)
**Milestones** are detected patterns in labor/postpartum events.

**Examples**:
- **5-1-1**: 5 contractions in 1 hour, lasting 1 minute each, 1 minute apart → transitional labor
- **3-1-1**: 3 contractions in 10 minutes (earlier labor)
- **Regression**: Contractions suddenly decrease (alarm signal)
- **Heavy bleeding**: Postpartum bleeding exceeds threshold

**Status**: Optional for v0.1 PoC. Backend has structure for rules; detection logic can be added later.

---

## Entities / Tables

### `cases` Table
| Column | Type | Notes |
|--------|------|-------|
| `case_id` | UUID | Primary key; unique |
| `status` | TEXT | 'active' or 'closed' |
| `join_code_hash` | TEXT | SHA256 hash of join code; unique |
| `join_code_last_rotated_at` | TIMESTAMPTZ | When code was last rotated |
| `created_at` | TIMESTAMPTZ | Immutable |
| `closed_at` | TIMESTAMPTZ | NULL until case closed |

### `events` Table
| Column | Type | Notes |
|--------|------|-------|
| `event_id` | UUID | Primary key; client-provided; unique constraint |
| `case_id` | UUID | Foreign key to `cases`; indexed |
| `event_seq` | BIGSERIAL | Auto-increment; used for cursor pagination |
| `type` | TEXT | Event type string |
| `ts` | TIMESTAMPTZ | Client-provided timestamp |
| `server_ts` | TIMESTAMPTZ | Server-generated timestamp; indexed |
| `track` | TEXT | 'labor', 'postpartum', or 'meta' (check constraint) |
| `source` | TEXT | 'woman', 'midwife', or 'system' (check constraint) |
| `payload_v` | INT | Schema version (default 1) |
| `payload` | JSONB | Event-specific data |

**Indexes**:
- `(case_id, event_seq)` – for cursor-based pagination
- `(case_id, server_ts)` – for timestamp-based queries (future use)

---

## Roles & Access

### Midwife
- **Login**: Email + password (PoC: any username/password)
- **Token scope**: Organization + assigned cases (future: case assignment table)
- **Can do**: Create/list/close cases, view all events, manage alerts, log notes/visit tasks
- **Cannot do**: Log labor/postpartum events for a woman (only she can)

### Woman
- **Join**: Join code → case-scoped JWT
- **Token scope**: Single case only
- **Can do**: Log labor/postpartum events, sync offline queue
- **Cannot do**: See midwife labels, close case, access other cases, see other women

---

## API Concepts

### RESTful Endpoints
- `POST /cases` – create
- `GET /cases` – list (with cursor pagination)
- `GET /cases/{id}` – read
- `POST /cases/{id}/rotate-join-code` – action
- `POST /cases/{id}/close` – action
- `POST /events/sync` – action (idempotent)
- `GET /cases/{id}/events` – list (cursor pagination)

### Idempotency
An operation is **idempotent** if calling it multiple times has the same effect as calling it once.

**Example**: `POST /events/sync` with the same `event_id` twice → same response, only stored once.

**Mechanism**: Check `event_id` in DB; if already exists, skip insert, include in `accepted_event_ids`.

### Status Codes
- `200 OK`: Success
- `400 Bad Request`: Invalid input (bad cursor, missing required field)
- `401 Unauthorized`: Missing/invalid token
- `403 Forbidden`: Token exists but insufficient scope (e.g., woman token accessing wrong case)
- `404 Not Found`: Case/event not found
- `500 Internal Server Error`: Unexpected server error

