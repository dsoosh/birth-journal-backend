# PoC Gap Analysis

**Last Updated:** December 31, 2025  
**Status:** ~80% Complete

This document outlines what's missing to bring the Położne PoC to 100% based on the documented requirements in `requirements.md` and `context.md`.

---

## Summary

| Category | Status | Effort |
|----------|--------|--------|
| Case Lifecycle | ✅ Complete | - |
| Contraction Tracking | ✅ Complete | - |
| Labor Events | ✅ Complete | - |
| Postpartum Check-ins | ✅ Complete | - |
| Midwife Dashboard | ✅ Complete | - |
| Midwife Reactions | ✅ Complete | - |
| Real-time Sync | ✅ Complete | - |
| Offline Queue | ✅ Complete | - |
| **Milestone Detection** | ❌ Missing | 3-5 days |
| **Alert System (Backend)** | ⚠️ Partial | 2-3 days |
| **Push Notifications** | ❌ Missing | 3-5 days |
| **Visit Tasks Workflow** | ⚠️ Partial | 1-2 days |

**Estimated Total Effort to 100%:** 9-15 developer-days

---

## Completed Features ✅

### 1. Case Lifecycle
- [x] Create case (midwife-initiated and patient-initiated flows)
- [x] Join case via QR code / join code
- [x] Case claim by midwife
- [x] Case status checking (claimed, labor_active, postpartum_active)
- [x] Case close/archive
- [x] Rotate join code
- [x] Multi-case support in patient app

### 2. Labor Track

#### Contraction Logging
- [x] Start/End contraction with timer
- [x] Duration tracking
- [x] Event sync to backend
- [x] Contractions timeline display

#### Labor Events
- [x] All event types: waters_breaking, mucus_plug, bleeding, reduced_fetal_movement, belly_lowering, nausea, urge_to_push, headache_vision, fever_chills
- [x] Severity levels (low/medium/high)
- [x] Optional notes
- [x] Midwife reactions (ack, coming, ok, seen)

### 3. Postpartum Track
- [x] Postpartum check-in forms
- [x] Mode switching (labor ↔ postpartum)
- [x] Postpartum-specific symptom buttons

### 4. Midwife Dashboard
- [x] Cases list with status indicators
- [x] Case detail view with event timeline
- [x] Real-time event updates via WebSocket
- [x] Event filtering and display
- [x] Login/authentication

### 5. Offline Support
- [x] Event queue in patient app
- [x] Cursor-based sync
- [x] Idempotent event handling
- [x] Reconnection handling

### 6. Real-time Communication
- [x] WebSocket endpoint for case events
- [x] Event broadcasting to connected clients
- [x] Midwife reactions propagate to patient app

---

## Missing Features (Required for 100%)

### 1. Milestone Detection System ❌ (3-5 days)

**Requirement:** System should automatically detect labor milestones from contraction patterns.

**Missing:**
- Backend milestone detection engine
- Pattern analysis for contractions (5-1-1, 3-1-1)
- Regression detection (pattern becoming irregular)
- Abnormal gap detection (no contractions after established pattern)
- Auto-generation of `alert_triggered` events

**Implementation Plan:**
```
backend/app/milestones/
├── __init__.py
├── detector.py          # Pattern detection logic
├── rules.py             # 5-1-1, 3-1-1, regression rules
└── scheduler.py         # Background task to check patterns
```

**Key Tasks:**
1. Create sliding window analyzer for contraction events
2. Implement 5-1-1 rule (5 min apart, 1 min duration, 1 hour sustained)
3. Implement 3-1-1 rule (3 min apart, 1 min duration, 1 hour sustained)
4. Implement regression detection
5. Implement abnormal gap detection
6. Generate `alert_triggered` events when milestones detected
7. Add background scheduler (every 5 minutes per active case)

**Effort:** 3-5 developer-days

---

### 2. Alert System - Full Implementation ⚠️ (2-3 days)

**Requirement:** Alert inbox with filtering, acknowledgement, and resolution.

**Current State:**
- Alert endpoints exist but return empty stubs
- `alert_ack` and `alert_resolve` events can be created
- No actual alert querying or filtering

**Missing:**
- `GET /alerts` - query active alerts across all cases
- `GET /cases/{case_id}/alerts` - query alerts for a case
- Alert severity-based filtering
- Active alert computation (triggered - resolved)
- Alert inbox UI in midwife app

**Implementation Plan:**
1. Implement alert query in `router.py` (scan `alert_triggered` events, filter out resolved)
2. Add severity filtering
3. Update `active_alerts` count in cases list
4. Create AlertsScreen UI (already exists as stub)
5. Add alert badge to navigation

**Effort:** 2-3 developer-days

---

### 3. Push Notifications ❌ (3-5 days)

**Requirement:** Midwife receives push notifications for critical alerts.

**Missing:**
- Firebase Cloud Messaging (FCM) integration
- APNs integration for iOS
- Device token registration endpoint
- Notification trigger on alert_triggered events
- Notification preferences

**Implementation Plan:**
```
backend/app/notifications/
├── __init__.py
├── fcm.py              # Firebase Cloud Messaging client
├── apns.py             # Apple Push Notification service
└── service.py          # Send notification on alert
```

**Mobile Changes:**
- Add `firebase_messaging` to Flutter apps
- Implement token registration on app startup
- Handle foreground/background notifications

**Key Tasks:**
1. Set up Firebase project and get credentials
2. Add FCM SDK to backend
3. Create device token storage (new table: `device_tokens`)
4. Add `POST /devices/register` endpoint
5. Integrate notification sending in milestone detector
6. Add Flutter FCM client to midwife app
7. Test on Android and iOS

**Effort:** 3-5 developer-days

---

### 4. Visit Tasks Workflow ⚠️ (1-2 days)

**Requirement:** Midwife can create visit tasks with planned date and status.

**Current State:**
- `visit_task` event type is documented
- No dedicated UI for managing visits

**Missing:**
- Visit creation UI in midwife app
- Visit list view per case
- Visit status updates (planned → done)
- Visit notes

**Implementation Plan:**
1. Add "Visits" tab to case detail screen
2. Create visit task dialog
3. Display visits timeline
4. Add status toggle (planned/done)

**Effort:** 1-2 developer-days

---

## Optional Enhancements (Not Required for PoC)

These are documented as optional in `requirements.md`:

| Feature | Effort | Priority |
|---------|--------|----------|
| Breastfeeding tracking | 1 day | Low |
| Mood tracking | 1 day | Low |
| Contraction statistics dashboard | 2 days | Medium |
| Multi-language improvements | 1 day | Medium |
| Dark mode | 0.5 days | Low |

---

## Technical Debt

| Issue | Effort | Impact |
|-------|--------|--------|
| Remove debug print statements | 0.5 days | Low |
| Add proper logging | 1 day | Medium |
| Error handling improvements | 1 day | Medium |
| API response validation | 0.5 days | Low |
| Test coverage improvement | 2-3 days | High |

---

## Recommended Priority Order

1. **Milestone Detection** - Core differentiating feature
2. **Alert System** - Required for milestone detection to be useful
3. **Push Notifications** - Critical for real-world use
4. **Visit Tasks** - Nice to have for PoC

---

## Definition of Done (100% PoC)

- [ ] Milestone detection generates alerts automatically
- [ ] Midwife receives push notifications for high-severity alerts
- [ ] Alert inbox shows active alerts with filtering
- [ ] Visit tasks can be created and marked done
- [ ] All documented event types are functional end-to-end
- [ ] Integration tests cover critical paths
- [ ] No critical bugs in offline sync
