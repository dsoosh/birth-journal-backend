"""
Integration tests for the API endpoints.

These tests cover full API flows across multiple endpoints,
simulating real-world usage patterns.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def _auth(client: TestClient, token: str) -> dict:
    """Helper to create Authorization header."""
    return {"Authorization": f"Bearer {token}"}


def _event(case_id: uuid.UUID, event_type: str, payload: dict | None = None) -> dict:
    """Helper to create event envelope."""
    return {
        "event_id": str(uuid.uuid4()),
        "case_id": str(case_id),
        "type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        "payload_v": 1,
        "payload": payload or {},
    }


# -----------------------------------------------------------------------------
# Full Flow Integration Tests
# -----------------------------------------------------------------------------


class TestMidwifeCreatesCaseAndPatientJoins:
    """Integration test: Complete case creation and join flow."""

    def test_full_case_creation_flow(self, client: TestClient):
        """
        Scenario:
        1. Midwife logs in
        2. Midwife creates a new case
        3. Patient joins via join code
        4. Patient submits events
        5. Midwife retrieves events
        """
        # Step 1: Create test midwife and login
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        midwife_pw = "testpassword123"
        
        # Create test account (dev endpoint)
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": midwife_pw,
        })
        assert resp.status_code == 200
        midwife_token = resp.json()["token"]
        
        # Step 2: Create a new case (returns 200 OK)
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        case_data = resp.json()
        case_id = uuid.UUID(case_data["case_id"])
        join_code = case_data["join_code"]
        
        assert join_code is not None
        assert len(join_code) == 6  # Standard join code length
        
        # Step 3: Patient joins via join code
        resp = client.post(
            "/api/v1/cases/join",
            json={"join_code": join_code},
        )
        assert resp.status_code == 200
        patient_token = resp.json()["token"]
        assert uuid.UUID(resp.json()["case_id"]) == case_id
        
        # Step 4: Patient submits contraction events
        contraction_start_id = str(uuid.uuid4())
        contraction_end_id = str(uuid.uuid4())
        
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={
                "cursor": None,
                "events": [
                    {
                        "event_id": contraction_start_id,
                        "case_id": str(case_id),
                        "type": "contraction_start",
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "payload_v": 1,
                        "payload": {},
                    },
                    {
                        "event_id": contraction_end_id,
                        "case_id": str(case_id),
                        "type": "contraction_end",
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "payload_v": 1,
                        "payload": {"duration_sec": 65},
                    },
                ],
            },
        )
        assert resp.status_code == 200
        sync_result = resp.json()
        assert contraction_start_id in [str(eid) for eid in sync_result["accepted_event_ids"]]
        assert contraction_end_id in [str(eid) for eid in sync_result["accepted_event_ids"]]
        
        # Step 5: Midwife retrieves events for the case
        resp = client.get(
            f"/api/v1/cases/{case_id}/events",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        events_feed = resp.json()
        event_types = [e["type"] for e in events_feed["events"]]
        assert "contraction_start" in event_types
        assert "contraction_end" in event_types
        
        # Step 6: Patient submits a high-severity bleeding event
        bleeding_event_id = str(uuid.uuid4())
        
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={
                "cursor": None,
                "events": [{
                    "event_id": bleeding_event_id,
                    "case_id": str(case_id),
                    "type": "labor_event",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "payload_v": 1,
                    "payload": {
                        "subtype": "bleeding",
                        "severity": "high",
                    },
                }],
            },
        )
        assert resp.status_code == 200
        
        # Step 7: Verify midwife can see all events including bleeding
        resp = client.get(
            f"/api/v1/cases/{case_id}/events",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        events = resp.json()["events"]
        event_types = [e["type"] for e in events]
        assert "labor_event" in event_types
        
        # Verify bleeding event details
        bleeding_events = [e for e in events if e["type"] == "labor_event"]
        assert len(bleeding_events) >= 1
        assert bleeding_events[0]["payload"]["subtype"] == "bleeding"


class TestPatientInitiatedCaseFlow:
    """Integration test: Patient initiates case, midwife claims it."""

    def test_patient_initiates_and_midwife_claims(self, client: TestClient):
        """
        Scenario:
        1. Patient initiates a new case
        2. Patient submits events
        3. Midwife logs in and claims the case
        4. Midwife can now see events
        """
        # Step 1: Patient initiates case (returns 200 OK)
        resp = client.post("/api/v1/cases/initiate")
        assert resp.status_code == 200
        init_data = resp.json()
        case_id = uuid.UUID(init_data["case_id"])
        join_code = init_data["join_code"]
        patient_token = init_data["token"]
        
        # Step 2: Patient submits events
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={
                "cursor": None,
                "events": [
                    _event(case_id, "contraction_start"),
                    _event(case_id, "contraction_end", {"duration_sec": 45}),
                ],
            },
        )
        assert resp.status_code == 200
        
        # Step 3: Create midwife and claim the case
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": "testpassword123",
        })
        midwife_token = resp.json()["token"]
        
        # Claim the case
        resp = client.post(
            "/api/v1/cases/claim",
            headers=_auth(client, midwife_token),
            json={"join_code": join_code},
        )
        assert resp.status_code == 200
        assert uuid.UUID(resp.json()["case_id"]) == case_id
        
        # Step 4: Midwife can see the case in their list
        resp = client.get(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        case_ids = [uuid.UUID(c["case_id"]) for c in resp.json()["cases"]]
        assert case_id in case_ids
        
        # Midwife can retrieve events
        resp = client.get(
            f"/api/v1/cases/{case_id}/events",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        events = resp.json()["events"]
        assert len(events) >= 2


class TestLaborToPostpartumTransition:
    """Integration test: Transitioning from labor to postpartum mode."""

    def test_mode_transition(self, client: TestClient):
        """
        Scenario:
        1. Create case
        2. Patient in labor mode - submit labor events
        3. Midwife sets postpartum mode active
        4. Patient submits postpartum check-in
        """
        # Setup: Create midwife and case
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": "testpassword123",
        })
        midwife_token = resp.json()["token"]
        
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        case_id = uuid.UUID(resp.json()["case_id"])
        join_code = resp.json()["join_code"]
        
        # Patient joins
        resp = client.post("/api/v1/cases/join", json={"join_code": join_code})
        patient_token = resp.json()["token"]
        
        # Step 1: Check initial status - Note: Midwife must use require_midwife endpoint
        # Patient can use /status endpoint
        resp = client.get(
            f"/api/v1/cases/{case_id}/status",
            headers=_auth(client, patient_token),
        )
        assert resp.status_code == 200
        # Labor is auto-activated when midwife creates case
        
        # Step 2: Activate labor mode using the correct endpoint
        resp = client.post(
            f"/api/v1/cases/{case_id}/set-labor",
            headers=_auth(client, midwife_token),
            json={"active": True},
        )
        assert resp.status_code == 200
        
        # Verify labor is active (patient uses /status)
        resp = client.get(
            f"/api/v1/cases/{case_id}/status",
            headers=_auth(client, patient_token),
        )
        assert resp.json()["labor_active"] is True
        
        # Step 3: Submit labor events
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={
                "cursor": None,
                "events": [
                    _event(case_id, "contraction_start"),
                    _event(case_id, "contraction_end", {"duration_sec": 60}),
                    _event(case_id, "labor_event", {
                        "subtype": "waters_breaking",
                        "notes": "Clear fluid",
                    }),
                ],
            },
        )
        assert resp.status_code == 200
        
        # Step 4: Transition to postpartum
        resp = client.post(
            f"/api/v1/cases/{case_id}/set-labor",
            headers=_auth(client, midwife_token),
            json={"active": False},
        )
        assert resp.status_code == 200
        
        resp = client.post(
            f"/api/v1/cases/{case_id}/set-postpartum",
            headers=_auth(client, midwife_token),
            json={"active": True},
        )
        assert resp.status_code == 200
        
        # Verify postpartum is active (patient checks via status)
        resp = client.get(
            f"/api/v1/cases/{case_id}/status",
            headers=_auth(client, patient_token),
        )
        assert resp.json()["labor_active"] is False
        assert resp.json()["postpartum_active"] is True
        
        # Step 5: Submit postpartum check-in
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={
                "cursor": None,
                "events": [
                    _event(case_id, "postpartum_checkin", {
                        "mood_score": 4,
                        "pain_score": 2,
                        "bleeding": "light",
                        "fever": False,
                        "notes": "Feeling better today",
                    }),
                ],
            },
        )
        assert resp.status_code == 200


class TestCursorBasedPagination:
    """Integration test: Cursor-based event pagination."""

    def test_pagination_with_cursor(self, client: TestClient):
        """
        Scenario:
        1. Create case
        2. Submit many events
        3. Paginate through events using cursor
        """
        # Setup
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": "testpassword123",
        })
        midwife_token = resp.json()["token"]
        
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        case_id = uuid.UUID(resp.json()["case_id"])
        join_code = resp.json()["join_code"]
        
        resp = client.post("/api/v1/cases/join", json={"join_code": join_code})
        patient_token = resp.json()["token"]
        
        # Submit 10 events
        events_to_submit = []
        for i in range(10):
            events_to_submit.append(_event(case_id, "contraction_start"))
            events_to_submit.append(_event(case_id, "contraction_end", {"duration_sec": 60 + i}))
        
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={"cursor": None, "events": events_to_submit},
        )
        assert resp.status_code == 200
        assert len(resp.json()["accepted_event_ids"]) == 20
        
        # Paginate with limit=5
        resp = client.get(
            f"/api/v1/cases/{case_id}/events?limit=5",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        page1 = resp.json()
        assert len(page1["events"]) == 5
        assert page1["next_cursor"] is not None
        
        # Get next page
        resp = client.get(
            f"/api/v1/cases/{case_id}/events?limit=5&cursor={page1['next_cursor']}",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        page2 = resp.json()
        assert len(page2["events"]) == 5
        
        # Ensure no duplicate events
        page1_ids = {e["event_id"] for e in page1["events"]}
        page2_ids = {e["event_id"] for e in page2["events"]}
        assert page1_ids.isdisjoint(page2_ids)


class TestCaseCloseAndArchive:
    """Integration test: Closing and archiving a case."""

    def test_case_close_flow(self, client: TestClient):
        """
        Scenario:
        1. Create case
        2. Submit some events
        3. Close the case
        4. Verify closed status
        """
        # Setup
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": "testpassword123",
        })
        midwife_token = resp.json()["token"]
        
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        case_id = uuid.UUID(resp.json()["case_id"])
        join_code = resp.json()["join_code"]
        
        resp = client.post("/api/v1/cases/join", json={"join_code": join_code})
        patient_token = resp.json()["token"]
        
        # Submit some events
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={
                "cursor": None,
                "events": [_event(case_id, "contraction_start")],
            },
        )
        assert resp.status_code == 200
        
        # Close the case
        resp = client.post(
            f"/api/v1/cases/{case_id}/close",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        
        # Verify status - patient can check their own case status
        resp = client.get(
            f"/api/v1/cases/{case_id}/status",
            headers=_auth(client, patient_token),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "closed"


class TestJoinCodeRotation:
    """Integration test: Join code rotation."""

    def test_rotate_join_code(self, client: TestClient):
        """
        Scenario:
        1. Create case
        2. Get original join code
        3. Rotate join code
        4. Old code no longer works
        5. New code works
        """
        # Setup
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": "testpassword123",
        })
        midwife_token = resp.json()["token"]
        
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        case_id = uuid.UUID(resp.json()["case_id"])
        old_code = resp.json()["join_code"]
        
        # Rotate the code
        resp = client.post(
            f"/api/v1/cases/{case_id}/rotate-join-code",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        new_code = resp.json()["join_code"]
        assert new_code != old_code
        
        # Old code should not work
        resp = client.post("/api/v1/cases/join", json={"join_code": old_code})
        assert resp.status_code == 404
        
        # New code should work
        resp = client.post("/api/v1/cases/join", json={"join_code": new_code})
        assert resp.status_code == 200


class TestTrackDerivedServerSide:
    """Integration test: Track field is derived server-side."""

    def test_track_override(self, client: TestClient):
        """
        Scenario:
        1. Submit event with wrong track value
        2. Server overrides with correct track
        """
        # Setup
        resp = client.post("/api/v1/cases/initiate")
        case_id = uuid.UUID(resp.json()["case_id"])
        patient_token = resp.json()["token"]
        
        # Submit event with wrong track
        event_id = str(uuid.uuid4())
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={
                "cursor": None,
                "events": [{
                    "event_id": event_id,
                    "case_id": str(case_id),
                    "type": "contraction_start",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "payload_v": 1,
                    "payload": {},
                    "track": "meta",  # Wrong track - should be "labor"
                }],
            },
        )
        assert resp.status_code == 200
        
        # Retrieve event and verify track
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_token),
            json={"cursor": None, "events": []},
        )
        new_events = resp.json()["new_events"]
        
        # Find our event
        our_event = next((e for e in new_events if e["event_id"] == event_id), None)
        assert our_event is not None
        assert our_event["track"] == "labor"  # Server corrected the track


class TestQRCodeGeneration:
    """Integration test: QR code generation for case joining."""

    def test_qr_code_endpoint(self, client: TestClient):
        """
        Scenario:
        1. Create a join code
        2. Generate QR code for the join code
        3. QR code contains valid data
        """
        # Setup - create midwife and case
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": "testpassword123",
        })
        midwife_token = resp.json()["token"]
        
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        assert resp.status_code == 200
        join_code = resp.json()["join_code"]
        
        # Generate QR code for the join code (not case-specific)
        resp = client.get(f"/api/v1/qr/join-code/{join_code}")
        assert resp.status_code == 200
        qr_data = resp.json()
        
        # QR data should contain join code
        assert "data" in qr_data
        assert join_code.upper() in qr_data["data"]


class TestAuthorizationScoping:
    """Integration test: Authorization scope enforcement."""

    def test_patient_cannot_access_other_cases(self, client: TestClient):
        """
        Scenario:
        1. Create two cases
        2. Patient from case A tries to access case B
        3. Access is denied
        """
        # Setup: Create midwife
        midwife_email = f"midwife_{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post("/api/v1/auth/test-account", json={
            "email": midwife_email,
            "password": "testpassword123",
        })
        midwife_token = resp.json()["token"]
        
        # Create case A
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        case_a_id = uuid.UUID(resp.json()["case_id"])
        join_code_a = resp.json()["join_code"]
        
        # Create case B
        resp = client.post(
            "/api/v1/cases",
            headers=_auth(client, midwife_token),
        )
        case_b_id = uuid.UUID(resp.json()["case_id"])
        
        # Patient joins case A
        resp = client.post("/api/v1/cases/join", json={"join_code": join_code_a})
        patient_a_token = resp.json()["token"]
        
        # Patient A tries to submit event to case B
        resp = client.post(
            "/api/v1/events/sync",
            headers=_auth(client, patient_a_token),
            json={
                "cursor": None,
                "events": [{
                    "event_id": str(uuid.uuid4()),
                    "case_id": str(case_b_id),
                    "type": "contraction_start",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "payload_v": 1,
                    "payload": {},
                }],
            },
        )
        # Event should be rejected
        assert resp.status_code == 200
        result = resp.json()
        assert len(result["rejected"]) == 1
        # The server rejects with "case_scope_violation"
        assert "case_scope_violation" in result["rejected"][0]["reason"].lower()
