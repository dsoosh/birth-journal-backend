from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel, Field
from pydantic import EmailStr


class HealthResponse(BaseModel):
    ok: bool
    db: bool


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class AuthLoginResponse(BaseModel):
    token: str


class TestAccountRequest(BaseModel):
    email: EmailStr
    password: str


class TestAccountResponse(BaseModel):
    email: EmailStr
    token: str


class CreateCaseResponse(BaseModel):
    case_id: uuid.UUID
    join_code: str


class InitiateCaseResponse(BaseModel):
    case_id: uuid.UUID
    join_code: str
    token: str


class ClaimCaseRequest(BaseModel):
    join_code: str


class ClaimCaseResponse(BaseModel):
    case_id: uuid.UUID


class CaseStatusResponse(BaseModel):
    case_id: uuid.UUID
    status: str
    claimed: bool


class JoinCaseRequest(BaseModel):
    join_code: str


class JoinCaseResponse(BaseModel):
    token: str
    case_id: uuid.UUID


class QRResponse(BaseModel):
    qr_data_uri: str | None
    data: str


class EventEnvelopeIn(BaseModel):
    event_id: uuid.UUID
    case_id: uuid.UUID | None = None
    type: str
    ts: dt.datetime
    track: str | None = None
    source: str | None = None
    payload_v: int | None = Field(default=1)
    payload: dict = Field(default_factory=dict)


class EventEnvelopeOut(BaseModel):
    event_id: uuid.UUID
    case_id: uuid.UUID
    type: str
    ts: dt.datetime
    server_ts: dt.datetime
    track: str
    source: str
    payload_v: int
    payload: dict


class SyncRequest(BaseModel):
    client_time: dt.datetime | None = None
    cursor: str | None = None
    events: list[EventEnvelopeIn] = Field(default_factory=list)


class SyncRejected(BaseModel):
    event_id: uuid.UUID
    reason: str


class SyncResponse(BaseModel):
    accepted_event_ids: list[uuid.UUID]
    rejected: list[SyncRejected]
    server_cursor: str
    new_events: list[EventEnvelopeOut]


class EventsFeedResponse(BaseModel):
    server_cursor: str
    next_cursor: str | None
    events: list[EventEnvelopeOut]


class CasesListItem(BaseModel):
    case_id: uuid.UUID
    label: str | None = None
    labor_active: bool
    postpartum_active: bool
    last_event_ts: dt.datetime | None
    active_alerts: int = 0


class CasesListResponse(BaseModel):
    cases: list[CasesListItem]
    server_cursor: str
    next_cursor: str | None
