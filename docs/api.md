# API (PoC)

Base path: `/api/v1`  
Style: REST + event-based sync  
All writes are append-only events.

---

## MVP endpoint set (summary)

| Area | Method | Path | Notes |
| --- | --- | --- | --- |
| Auth | POST | /auth/login | Midwife login, returns JWT |
| Auth | POST | /cases/join | Woman joins via join code, returns case token (legacy) |
| Cases | POST | /cases/initiate | Patient initiates case, gets join code + token |
| Cases | POST | /cases/claim | Midwife claims case using patient's join code |
| Cases | GET | /cases/{case_id}/status | Check if case is claimed |
| Cases | POST | /cases | Create case + join code (legacy midwife-initiated) |
| Cases | GET | /cases | Midwife list (supports summary view) |
| Cases | GET | /cases/{case_id} | Case details |
| Cases | POST | /cases/{case_id}/rotate-join-code | Rotate join code |
| Cases | POST | /cases/{case_id}/close | Close/archive case |
| Events | POST | /events/sync | Append events + receive new events |
| Events | GET | /cases/{case_id}/events | Read-only event feed for UI |
| Alerts | GET | /alerts | Midwife alert inbox (all cases) |
| Alerts | POST | /cases/{case_id}/alerts/{alert_event_id}/ack | Acknowledge |
| Alerts | POST | /cases/{case_id}/alerts/{alert_event_id}/resolve | Resolve |

---

## Authentication

### Midwife
- `POST /auth/login`
- Returns JWT with role `midwife`
- Token scope: organization + assigned cases

### Patient (new flow)
- `POST /cases/initiate` (no auth required)
- Returns: `{ "case_id", "join_code", "token" }`
- Patient shows join code/QR to midwife
- Token scope: single `case_id` only

### Patient (legacy flow)
- `POST /cases/join`
- Body: `{ "join_code": "ABCD12" }`
- Returns case-scoped JWT
- Token scope: single `case_id` only

---

## Core resources

### Case

#### Initiate case (patient)
`POST /cases/initiate`

Response:
- `case_id`
- `join_code` (for midwife to scan/enter)
- `token` (case-scoped JWT for patient)

Patient shows the join code to midwife. Case remains unclaimed until midwife calls `/cases/claim`.

#### Claim case (midwife)
`POST /cases/claim`

Request:
- `join_code`

Requires midwife authentication. Binds the midwife to the case and rotates the join code.

Response:
- `case_id`

#### Check case status (patient)
`GET /cases/{case_id}/status`

Requires patient case token. Returns:
- `case_id`
- `status` (`active` | `closed`)
- `claimed` (boolean - true if midwife has claimed)

Patient polls this to detect when a midwife has paired.

#### Create case (midwife - legacy)
`POST /cases`

Response:
- `case_id`
- `join_code`

#### List cases (midwife)
`GET /cases`

Query:
- `status` = `active | closed` (default `active`)
- `view` = `summary | full` (default `summary`)
- `limit` = `1..200` (default `50`)
- `cursor` = `opaque` (for pagination)

Summary response:

    {
      "cases": [
        {
          "case_id": "uuid",
          "label": "display name or code (midwife-only)",
          "labor_active": true,
          "postpartum_active": false,
          "last_event_ts": "ISO-8601 UTC",
          "active_alerts": 2
        }
      ],
      "server_cursor": "opaque",
      "next_cursor": "opaque-or-null"
    }

Case state flags (deterministic):
- `labor_active` and `postpartum_active` are server-derived convenience flags, computed from the latest `set_labor_active` / `set_postpartum_active` events for the case (default `false` if never set).
- If the case is `closed`, both flags are `false` regardless of prior toggles.

#### Rotate join code (midwife)
`POST /cases/{case_id}/rotate-join-code`

#### Join case (woman)
`POST /cases/join`

Request:
- `join_code`

Response:
- case-scoped token  
- minimal case metadata
- no midwife-only labels or identity fields

#### Get case
`GET /cases/{case_id}`

#### Close case (midwife)
`POST /cases/{case_id}/close`

---

## Events (append-only)

All domain activity is recorded as events.

### Event envelope

    {
      "event_id": "uuid",
      "case_id": "uuid",
      "type": "string",
      "ts": "ISO-8601 UTC",
      "server_ts": "ISO-8601 UTC",
      "track": "labor | postpartum | meta",
      "source": "woman | midwife | system",
      "payload_v": 1,
      "payload": {}
    }

Notes:
- `track` is server-derived or validated. Clients may omit it; server assigns canonical track by `type`.
- Clients should not use `track` for client-side logic; rely on `type` instead.
- `server_ts` is added by the server on ingest; clients should ignore it on send.
- `payload_v` defaults to `1` if omitted.

---

### Event sync (offline-tolerant)

`POST /events/sync`

Request:

    {
      "client_time": "ISO-8601",
      "cursor": "opaque-or-null",
      "events": [ { "event envelope" } ]
    }

`client_time` is the device time when the sync request was sent (informational only; useful for debugging clock skew).

Response:

    {
      "accepted_event_ids": ["uuid"],
      "rejected": [
        { "event_id": "uuid", "reason": "string" }
      ],
      "server_cursor": "opaque",
      "new_events": [ { "event envelope" } ]
    }

Rules:
- `event_id` must be client-generated UUID
- server is idempotent
- duplicates are ignored safely
- server may override or set `track` if omitted or incorrect
- server adds `server_ts` for ordering across clients
- `cursor` is an opaque, server-issued, monotonic continuation token; timestamps are not valid cursors
- clients should persist the latest `server_cursor` and send it back as `cursor` on the next sync

---

### Event feed (read-only)

`GET /cases/{case_id}/events`

Query:
- `cursor` = `opaque-or-null` (continuation cursor)
- `limit` = `1..200` (default `50`)

Response:

    {
      "server_cursor": "opaque",
      "next_cursor": "opaque-or-null",
      "events": [ { "event envelope" } ]
    }

---

## Event types (PoC)

Note: Contraction event types are supported but not required; backend may ignore them in early PoC phases.

### Labor — contractions

**contraction_start**

    {
      "local_seq": 12
    }

**contraction_end**

    {
      "duration_s": 62
    }

---

### Labor — notable events (woman)

**labor_event**

    {
      "kind": "waters_breaking | mucus_plug | bleeding | reduced_fetal_movement | belly_lowering | nausea | urge_to_push | headache_vision | fever_chills | other",
      "severity": "low | medium | high",
      "note": "optional text"
    }

---

### Postpartum check-in (woman)

**postpartum_checkin**

    {
      "items": {
        "bleeding": "none | light | moderate | heavy",
        "fever": "no | yes",
        "headache_vision": "no | yes",
        "pain": "none | mild | moderate | severe"
      },
      "note": "optional text"
    }

---

### Midwife events

**note**

    {
      "text": "free text"
    }

**visit_task**

    {
      "due_date": "YYYY-MM-DD",
      "status": "planned | done",
      "note": "optional text"
    }

**set_labor_active**

    {
      "active": true
    }

**set_postpartum_active**

    {
      "active": true
    }

---

## Derived events (system)

### Alert triggered

**alert_triggered**

    {
      "alert_code": "MILESTONE_511 | MILESTONE_311 | REGRESSION | ABNORMAL_GAP | HEAVY_BLEEDING",
      "severity": "info | warning | urgent",
      "explain": {
        "rule_version": "ruleset-0.1",
        "window_minutes": 60,
        "summary": "human-readable explanation"
      }
    }

Alerts are events.  
Acknowledgement and resolution are also events.

Alert lifecycle:
- Active alerts = `alert_triggered` minus `alert_resolve` by `alert_event_id`.
- `alert_ack` marks review only; it does not resolve or suppress future alerts.
- Multiple alerts with the same `alert_code` can be active at once.

---

### Alert acknowledgement

**alert_ack**

    {
      "alert_event_id": "uuid"
    }

### Alert resolution

**alert_resolve**

    {
      "alert_event_id": "uuid"
    }

---

## Convenience endpoints (optional)

All can be derived from events; these exist for UI simplicity.

- `GET /cases/{case_id}/alerts`
- `GET /alerts`
- `POST /cases/{case_id}/alerts/{alert_event_id}/ack`
- `POST /cases/{case_id}/alerts/{alert_event_id}/resolve`

The `.../ack` and `.../resolve` endpoints are thin wrappers that create `alert_ack` / `alert_resolve` events (and return the created event envelope, or its `event_id`).

### Alert inbox (midwife)

`GET /alerts`

Query:
- `status` = `active | all` (default `active`)
- `limit` = `1..200` (default `50`)
- `cursor` = `opaque` (for pagination)

Response:

    {
      "alerts": [ { "event envelope" } ],
      "server_cursor": "opaque",
      "next_cursor": "opaque-or-null"
    }

---

## Versioning

- API version in base path (`/v1`)
- Rule version stored in derived event payload
- Breaking changes require new API version

---

## Design guarantees

- Append-only, auditable history
- Deterministic rule outputs
- Offline-safe, idempotent sync
- No hidden state outside events
