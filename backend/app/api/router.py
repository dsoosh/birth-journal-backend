from __future__ import annotations

import asyncio
import datetime as dt
import uuid

import sqlalchemy as sa
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from backend.app.auth import mint_case_token, mint_midwife_token, require_case, require_midwife
from backend.app.db import get_db
from backend.app.join_code import generate_join_code, hash_join_code
from backend.app.models import Case, Event, Midwife
from backend.app.track import derive_track
from backend.app.qr import generate_qr_code
from backend.app.password import hash_password, verify_password
from backend.app.ws_manager import manager

from .schemas import (
	AuthLoginRequest,
	AuthLoginResponse,
	CasesListItem,
	CasesListResponse,
	CaseStatusResponse,
	ClaimCaseRequest,
	ClaimCaseResponse,
	CreateCaseResponse,
	EventEnvelopeOut,
	EventsFeedResponse,
	HealthResponse,
	InitiateCaseResponse,
	JoinCaseRequest,
	JoinCaseResponse,
	QRResponse,
	SyncRejected,
	SyncRequest,
	SyncResponse,
	TestAccountRequest,
	TestAccountResponse,
)

router = APIRouter(prefix="/api/v1")


def _utcnow() -> dt.datetime:
	return dt.datetime.now(dt.timezone.utc)


def _parse_cursor(cursor: str | None) -> int:
	if cursor is None or cursor == "":
		return 0
	try:
		value = int(cursor)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail="invalid_cursor") from exc
	if value < 0:
		raise HTTPException(status_code=400, detail="invalid_cursor")
	return value


def _to_event_out(row: Event) -> EventEnvelopeOut:
	return EventEnvelopeOut(
		event_id=row.event_id,
		case_id=row.case_id,
		type=row.type,
		ts=row.ts,
		server_ts=row.server_ts,
		track=row.track,
		source=row.source,
		payload_v=row.payload_v,
		payload=row.payload,
	)


@router.get("/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
	try:
		db.execute(sa.text("SELECT 1"))
		db_ok = True
	except Exception:
		db_ok = False
	return HealthResponse(ok=True, db=db_ok)


@router.post("/auth/login", response_model=AuthLoginResponse)
def auth_login(body: AuthLoginRequest, db: Session = Depends(get_db)) -> AuthLoginResponse:
	"""Authenticate with email/password and return JWT."""
	midwife = db.scalar(sa.select(Midwife).where(Midwife.email == body.email))
	if midwife is None or not verify_password(body.password, midwife.password_hash):
		raise HTTPException(status_code=401, detail="invalid_credentials")

	token = mint_midwife_token(sub=str(midwife.midwife_id))
	return AuthLoginResponse(token=token)


@router.post("/auth/test-account", response_model=TestAccountResponse)
def create_test_account(body: TestAccountRequest, db: Session = Depends(get_db)) -> TestAccountResponse:
	"""Create or reuse a test midwife account (email+password) and return a token."""
	if not body.email or not body.password:
		raise HTTPException(status_code=400, detail="invalid_credentials")

	# Check if account already exists
	existing = db.scalar(sa.select(Midwife).where(Midwife.email == body.email))
	if existing is not None:
		# Account exists; verify password
		if not verify_password(body.password, existing.password_hash):
			raise HTTPException(status_code=401, detail="invalid_credentials")
		midwife = existing
	else:
		# Create new account
		midwife = Midwife(
			email=body.email,
			password_hash=hash_password(body.password),
		)
		db.add(midwife)
		db.commit()
		db.refresh(midwife)

	token = mint_midwife_token(sub=str(midwife.midwife_id))
	return TestAccountResponse(email=body.email, token=token)


@router.post("/cases", response_model=CreateCaseResponse)
def create_case(principal: object = Depends(require_midwife), db: Session = Depends(get_db)) -> CreateCaseResponse:
	"""Midwife creates a new case and receives a join code to share with the patient."""
	midwife_id = uuid.UUID(principal.sub)
	join_code = generate_join_code()
	case = Case(join_code_hash=hash_join_code(join_code), midwife_id=midwife_id)
	db.add(case)
	db.commit()
	db.refresh(case)
	return CreateCaseResponse(case_id=case.case_id, join_code=join_code)


@router.post("/cases/initiate", response_model=InitiateCaseResponse)
def initiate_case(db: Session = Depends(get_db)) -> InitiateCaseResponse:
	"""Patient initiates a new case and receives a join code for the midwife to claim."""
	join_code = generate_join_code()
	case = Case(join_code_hash=hash_join_code(join_code), midwife_id=None)
	db.add(case)
	db.commit()
	db.refresh(case)
	
	token = mint_case_token(case_id=str(case.case_id))
	return InitiateCaseResponse(case_id=case.case_id, join_code=join_code, token=token)


@router.post("/cases/claim", response_model=ClaimCaseResponse)
def claim_case(body: ClaimCaseRequest, principal: object = Depends(require_midwife), db: Session = Depends(get_db)) -> ClaimCaseResponse:
	"""Midwife claims an unclaimed case using the patient's join code."""
	midwife_id = uuid.UUID(principal.sub)
	join_hash = hash_join_code(body.join_code)
	
	case = db.scalar(
		sa.select(Case).where(
			Case.join_code_hash == join_hash,
			Case.status == "active",
			Case.midwife_id.is_(None)
		)
	)
	if case is None:
		raise HTTPException(status_code=404, detail="case_not_found_or_already_claimed")
	
	# Claim the case and rotate join code
	case.midwife_id = midwife_id
	new_join_code = generate_join_code()
	case.join_code_hash = hash_join_code(new_join_code)
	case.join_code_last_rotated_at = _utcnow()
	
	# Auto-set case to labor mode when claimed
	now = _utcnow()
	labor_event = Event(
		event_id=uuid.uuid4(),
		case_id=case.case_id,
		type="set_labor_active",
		ts=now,
		server_ts=now,
		track=derive_track("set_labor_active"),
		source="system",
		payload_v=1,
		payload={"active": True, "auto_set_on_claim": True},
	)
	db.add(labor_event)
	db.commit()
	
	return ClaimCaseResponse(case_id=case.case_id)


@router.get("/cases/{case_id}/status", response_model=CaseStatusResponse)
def get_case_status(case_id: uuid.UUID, principal: object = Depends(require_case), db: Session = Depends(get_db)) -> CaseStatusResponse:
	"""Get case status - patient uses this to check if a midwife has claimed the case."""
	# Verify the case_id matches the token's case_id
	if str(case_id) != principal.case_id:
		raise HTTPException(status_code=403, detail="forbidden")
	
	case = db.scalar(sa.select(Case).where(Case.case_id == case_id))
	if case is None:
		raise HTTPException(status_code=404, detail="case_not_found")
	
	return CaseStatusResponse(
		case_id=case.case_id,
		status=case.status,
		claimed=case.midwife_id is not None
	)


@router.post("/cases/join", response_model=JoinCaseResponse)
def join_case(body: JoinCaseRequest, db: Session = Depends(get_db)) -> JoinCaseResponse:
    join_hash = hash_join_code(body.join_code)
    case = db.scalar(sa.select(Case).where(Case.join_code_hash == join_hash, Case.status == "active"))
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")

    token = mint_case_token(case_id=str(case.case_id))
    return JoinCaseResponse(token=token, case_id=case.case_id)


@router.get("/qr/app-link")
def qr_app_link() -> QRResponse:
    """Generate QR code for the app entry point (woman scans to join)."""
    app_url = "http://localhost:8000"  # In production, use your app domain
    qr_data = generate_qr_code(app_url)
    return QRResponse(qr_data_uri=qr_data, data=app_url)


@router.get("/qr/join-code/{join_code}")
def qr_join_code(join_code: str) -> QRResponse:
    """Generate QR code for a join code (woman shows to midwife to scan)."""
    qr_data = generate_qr_code(join_code.upper())
    return QRResponse(qr_data_uri=qr_data, data=join_code.upper())


@router.get("/cases/{case_id}", response_model=dict)
def get_case(case_id: uuid.UUID, _: object = Depends(require_midwife), db: Session = Depends(get_db)) -> dict:
    case = db.scalar(sa.select(Case).where(Case.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")

    return {
        "case_id": str(case.case_id),
        "status": case.status,
        "created_at": case.created_at.isoformat(),
        "closed_at": case.closed_at.isoformat() if case.closed_at else None,
    }


@router.post("/cases/{case_id}/rotate-join-code", response_model=dict)
def rotate_join_code(case_id: uuid.UUID, _: object = Depends(require_midwife), db: Session = Depends(get_db)) -> dict:
    case = db.scalar(sa.select(Case).where(Case.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")

    new_join_code = generate_join_code()
    case.join_code_hash = hash_join_code(new_join_code)
    case.join_code_last_rotated_at = _utcnow()
    db.commit()

    return {"case_id": str(case.case_id), "join_code": new_join_code}


@router.post("/cases/{case_id}/close", response_model=dict)
def close_case(case_id: uuid.UUID, _: object = Depends(require_midwife), db: Session = Depends(get_db)) -> dict:
    case = db.scalar(sa.select(Case).where(Case.case_id == case_id))
    if case is None:
        raise HTTPException(status_code=404, detail="case_not_found")

    case.status = "closed"
    case.closed_at = _utcnow()
    db.commit()

    return {"case_id": str(case.case_id), "status": case.status, "closed_at": case.closed_at.isoformat()}
@router.post("/events/sync", response_model=SyncResponse)
def events_sync(
	body: SyncRequest,
	background_tasks: BackgroundTasks,
	principal=Depends(require_case),
	db: Session = Depends(get_db),
	limit: int = Query(default=200, ge=1, le=200),
) -> SyncResponse:
	case_id = uuid.UUID(principal.case_id)
	since_seq = _parse_cursor(body.cursor)

	accepted: list[uuid.UUID] = []
	rejected: list[SyncRejected] = []

	if body.events:
		rows_to_insert: list[dict] = []
		for ev in body.events:
			if ev.case_id is not None and ev.case_id != case_id:
				rejected.append(SyncRejected(event_id=ev.event_id, reason="case_scope_violation"))
				continue

			track = derive_track(ev.type)
			source = "woman"
			payload_v = ev.payload_v or 1
			payload = ev.payload or {}
			rows_to_insert.append(
				{
					"event_id": ev.event_id,
					"case_id": case_id,
					"type": ev.type,
					"ts": ev.ts,
					"track": track,
					"source": source,
					"payload_v": payload_v,
					"payload": payload,
				}
			)

		if rows_to_insert:
			stmt = insert(Event).values(rows_to_insert)
			stmt = stmt.on_conflict_do_nothing(index_elements=[Event.event_id]).returning(Event.event_id)
			inserted_ids = list(db.execute(stmt).scalars().all())
			accepted.extend(inserted_ids)
			db.commit()
			
			# Broadcast newly accepted events via WebSocket
			print(f"Sync endpoint: {len(inserted_ids)} events accepted, broadcasting to WebSocket clients")
			print(f"Active connections: {manager.active_connections}")
			
			for event_id in inserted_ids:
				event = db.query(Event).filter_by(event_id=event_id).first()
				if event:
					event_out = _to_event_out(event)
					event_dict = event_out.model_dump(mode='json')
					print(f"Event dict keys: {event_dict.keys()}")
					print(f"Event ts: {event_dict.get('ts')} (type: {type(event_dict.get('ts'))})")
					print(f"Event server_ts: {event_dict.get('server_ts')} (type: {type(event_dict.get('server_ts'))})")
					
					message = {
						"type": "event",
						"case_id": str(case_id),
						"event": event_dict,
						"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
					}
					print(f"Broadcasting event {event_id} to case {case_id}: {message}")
					
					# Schedule async broadcast as background task
					case_id_str = str(case_id)
					if case_id_str in manager.active_connections:
						print(f"Found {len(manager.active_connections[case_id_str])} connections for case {case_id_str}")
						background_tasks.add_task(manager.broadcast, case_id_str, message)
						print(f"Scheduled broadcast for event {event_id}")
					else:
						print(f"No WebSocket connections for case {case_id_str}")

	new_rows = db.scalars(
		sa.select(Event)
		.where(Event.case_id == case_id, Event.event_seq > since_seq)
		.order_by(Event.event_seq.asc())
		.limit(limit)
	).all()

	new_events = [_to_event_out(r) for r in new_rows]
	max_seq = since_seq
	if new_rows:
		max_seq = max(r.event_seq for r in new_rows)

	return SyncResponse(
		accepted_event_ids=accepted,
		rejected=rejected,
		server_cursor=str(max_seq),
		new_events=new_events,
	)


@router.get("/cases/{case_id}/events", response_model=EventsFeedResponse)
def case_events_feed(
	case_id: uuid.UUID,
	_: object = Depends(require_midwife),
	db: Session = Depends(get_db),
	cursor: str | None = None,
	limit: int = Query(default=50, ge=1, le=200),
) -> EventsFeedResponse:
	since_seq = _parse_cursor(cursor)
	rows = db.scalars(
		sa.select(Event)
		.where(Event.case_id == case_id, Event.event_seq > since_seq)
		.order_by(Event.event_seq.asc())
		.limit(limit)
	).all()

	events = [_to_event_out(r) for r in rows]
	max_seq = since_seq
	if rows:
		max_seq = max(r.event_seq for r in rows)

	next_cursor = str(max_seq) if rows else None
	return EventsFeedResponse(server_cursor=str(max_seq), next_cursor=next_cursor, events=events)


@router.get("/cases", response_model=CasesListResponse)
def list_cases(
	status: str = Query(default="active", pattern="^(active|closed)$"),
	view: str = Query(default="summary", pattern="^(summary|full)$"),
	limit: int = Query(default=50, ge=1, le=200),
	cursor: str | None = None,
	_: object = Depends(require_midwife),
	db: Session = Depends(get_db),
) -> CasesListResponse:
	_ = view  # reserved for later
	since = _parse_cursor(cursor)

	stmt = (
		sa.select(Case)
		.where(Case.status == status)
		.order_by(Case.created_at.asc(), Case.case_id.asc())
		.offset(since)
		.limit(limit)
	)
	cases = db.scalars(stmt).all()

	items: list[CasesListItem] = []
	for c in cases:
		last_event_ts = db.scalar(sa.select(sa.func.max(Event.ts)).where(Event.case_id == c.case_id))

		def _latest_toggle(event_type: str) -> bool:
			active_text = db.scalar(
				sa.select(Event.payload["active"].astext)
				.where(Event.case_id == c.case_id, Event.type == event_type)
				.order_by(Event.event_seq.desc())
				.limit(1)
			)
			if active_text is None:
				return False
			return str(active_text).lower() == "true"

		labor_active = _latest_toggle("set_labor_active")
		postpartum_active = _latest_toggle("set_postpartum_active")
		if c.status == "closed":
			labor_active = False
			postpartum_active = False

		items.append(
			CasesListItem(
				case_id=c.case_id,
				label=None,
				labor_active=labor_active,
				postpartum_active=postpartum_active,
				last_event_ts=last_event_ts,
				active_alerts=0,
			)
		)

	next_cursor = str(since + len(cases)) if len(cases) == limit else None
	return CasesListResponse(cases=items, server_cursor=str(since), next_cursor=next_cursor)


@router.get("/alerts")
def alerts(_: object = Depends(require_midwife)) -> dict:
    # Not required for validating the event pipeline; return empty for now.
    return {"alerts": [], "server_cursor": "0", "next_cursor": None}


@router.get("/cases/{case_id}/alerts")
def case_alerts(case_id: uuid.UUID, _: object = Depends(require_midwife)) -> dict:
    # Not required for validating the event pipeline; return empty for now.
    return {"alerts": [], "server_cursor": "0", "next_cursor": None}


@router.post("/cases/{case_id}/alerts/{alert_event_id}/ack")
def alert_ack(case_id: uuid.UUID, alert_event_id: uuid.UUID, _: object = Depends(require_midwife), db: Session = Depends(get_db)) -> EventEnvelopeOut:
	ev = Event(
		event_id=uuid.uuid4(),
		case_id=case_id,
		type="alert_ack",
		ts=_utcnow(),
		track=derive_track("alert_ack"),
		source="midwife",
		payload_v=1,
		payload={"alert_event_id": str(alert_event_id)},
	)
	db.add(ev)
	db.commit()
	db.refresh(ev)
	return _to_event_out(ev)


@router.websocket("/ws/cases/{case_id}")
async def websocket_endpoint(
	websocket: WebSocket,
	case_id: str,
	token: str,
	db: Session = Depends(get_db),
):
	"""
	WebSocket endpoint for real-time case events.
	
	Query params:
	- token: JWT token (case-scoped or midwife-scoped)
	
	Connect with case JWT for patient or midwife JWT for midwife.
	Receives and broadcasts events in real-time.
	"""
	# Accept connection first
	await websocket.accept()
	
	# Validate case exists
	case = db.query(Case).filter_by(case_id=uuid.UUID(case_id)).first()
	if not case:
		await websocket.close(code=1008, reason="Case not found")
		return
	
	# Try to validate token
	try:
		import jwt
		from backend.app.settings import get_settings
		settings = get_settings()
		payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
		user_type = payload.get("role")  # "midwife" or "woman"
		user_id = payload.get("sub") or payload.get("case_id")
	except Exception:
		await websocket.close(code=1008, reason="Invalid token")
		return
	
	# Connect client (connection already accepted, just register it)
	connection_id = str(uuid.uuid4())
	if case_id not in manager.active_connections:
		manager.active_connections[case_id] = {}
	manager.active_connections[case_id][connection_id] = websocket
	manager.connection_ids[websocket] = connection_id
	
	# Send welcome message
	await manager.send_personal(
		websocket,
		{
			"type": "connection",
			"status": "connected",
			"case_id": case_id,
			"connection_id": connection_id,
			"user_type": user_type,
		},
	)
	
	try:
		print(f"WebSocket connection established: {connection_id} for case {case_id}")
		while True:
			try:
				# Use a timeout to avoid hanging forever
				# If client sends nothing for 30 seconds, send a ping
				data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
				
				# Broadcast to all clients in this case
				message = {
					"type": data.get("type", "message"),
					"case_id": case_id,
					"user_id": user_id,
					"user_type": user_type,
					"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
					"payload": data.get("payload", {}),
				}
				
				await manager.broadcast(case_id, message)
			except asyncio.TimeoutError:
				# Send a ping to keep the connection alive
				try:
					await websocket.send_json({"type": "ping"})
				except Exception as e:
					print(f"Failed to send ping to {connection_id}: {e}")
					break
	
	except WebSocketDisconnect as e:
		print(f"WebSocket disconnected: {connection_id} for case {case_id}")
		manager.disconnect(case_id, websocket)
	except Exception as e:
		print(f"WebSocket error for {connection_id}: {e}")
		manager.disconnect(case_id, websocket)

@router.post("/cases/{case_id}/alerts/{alert_event_id}/resolve")
def alert_resolve(
	case_id: uuid.UUID, alert_event_id: uuid.UUID, _: object = Depends(require_midwife), db: Session = Depends(get_db)
) -> EventEnvelopeOut:
	ev = Event(
		event_id=uuid.uuid4(),
		case_id=case_id,
		type="alert_resolve",
		ts=_utcnow(),
		track=derive_track("alert_resolve"),
		source="midwife",
		payload_v=1,
		payload={"alert_event_id": str(alert_event_id)},
	)
	db.add(ev)
	db.commit()
	db.refresh(ev)
	return _to_event_out(ev)


# Development endpoints (should be disabled in production)
@router.post("/dev/wipe")
def dev_wipe_database(db: Session = Depends(get_db)) -> dict:
	"""DANGEROUS: Wipe all data from the database. For development only."""
	# Delete in correct order to respect foreign keys
	db.execute(sa.delete(Event))
	db.execute(sa.delete(Case))
	db.execute(sa.delete(Midwife))
	db.commit()
	return {"status": "wiped", "message": "All data deleted"}

