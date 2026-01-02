from __future__ import annotations

import datetime as dt
import uuid


def _auth(client, token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _midwife_token(client) -> str:
    # Create a test midwife using the test-account endpoint
    email = f"midwife_sync_test_{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/api/v1/auth/test-account", json={"email": email, "password": "testpw123"})
    assert r.status_code == 200
    return r.json()["token"]


def _create_case(client) -> tuple[str, str]:
    mw = _midwife_token(client)
    r = client.post("/api/v1/cases", headers=_auth(client, mw))
    assert r.status_code == 200
    data = r.json()
    return data["case_id"], data["join_code"]


def _join_case(client, join_code: str) -> tuple[str, str]:
    r = client.post("/api/v1/cases/join", json={"join_code": join_code})
    assert r.status_code == 200
    data = r.json()
    return data["token"], data["case_id"]


def test_sync_idempotent_event_id(client):
    case_id, join_code = _create_case(client)
    token, _ = _join_case(client, join_code)

    event_id = str(uuid.uuid4())
    ev = {
        "event_id": event_id,
        "case_id": case_id,
        "type": "contraction_start",
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "track": "meta",  # intentionally wrong
        "source": "woman",
        "payload_v": 1,
        "payload": {"local_seq": 1},
    }

    r1 = client.post("/api/v1/events/sync", headers=_auth(client, token), json={"cursor": None, "events": [ev]})
    assert r1.status_code == 200
    assert event_id in [str(x) for x in r1.json()["accepted_event_ids"]]
    server_cursor_1 = r1.json()["server_cursor"]
    assert r1.json()["new_events"][0]["track"] == "labor"  # overridden

    r2 = client.post(
        "/api/v1/events/sync",
        headers=_auth(client, token),
        json={"cursor": server_cursor_1, "events": [ev]},
    )
    assert r2.status_code == 200
    assert r2.json()["accepted_event_ids"] == []
    assert r2.json()["new_events"] == []


def test_cursor_returns_only_new_events(client):
    case_id, join_code = _create_case(client)
    token, _ = _join_case(client, join_code)

    ev1 = {
        "event_id": str(uuid.uuid4()),
        "case_id": case_id,
        "type": "labor_event",
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "payload": {"kind": "mucus_plug", "severity": "low"},
    }
    r1 = client.post("/api/v1/events/sync", headers=_auth(client, token), json={"cursor": None, "events": [ev1]})
    assert r1.status_code == 200
    cur = r1.json()["server_cursor"]

    ev2 = {
        "event_id": str(uuid.uuid4()),
        "case_id": case_id,
        "type": "contraction_end",
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "payload": {"duration_s": 10},
    }
    r2 = client.post("/api/v1/events/sync", headers=_auth(client, token), json={"cursor": cur, "events": [ev2]})
    assert r2.status_code == 200
    assert len(r2.json()["new_events"]) == 1
    assert r2.json()["new_events"][0]["event_id"] == ev2["event_id"]


def test_auth_scope_woman_cannot_write_other_case(client):
    case_id_1, join_code_1 = _create_case(client)
    case_id_2, _join_code_2 = _create_case(client)

    token, _ = _join_case(client, join_code_1)

    ev = {
        "event_id": str(uuid.uuid4()),
        "case_id": case_id_2,  # malicious
        "type": "labor_event",
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "payload": {"kind": "bleeding", "severity": "high"},
    }
    r = client.post("/api/v1/events/sync", headers=_auth(client, token), json={"cursor": None, "events": [ev]})
    assert r.status_code == 200
    assert r.json()["accepted_event_ids"] == []
    assert r.json()["rejected"][0]["reason"] == "case_scope_violation"


def test_track_is_overridden_when_wrong(client):
    case_id, join_code = _create_case(client)
    token, _ = _join_case(client, join_code)

    ev = {
        "event_id": str(uuid.uuid4()),
        "case_id": case_id,
        "type": "postpartum_checkin",
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
        "track": "labor",  # wrong
        "payload": {"items": {"bleeding": "light", "fever": "no", "headache_vision": "no", "pain": "mild"}},
    }
    r = client.post("/api/v1/events/sync", headers=_auth(client, token), json={"cursor": None, "events": [ev]})
    assert r.status_code == 200
    assert r.json()["new_events"][0]["track"] == "postpartum"
