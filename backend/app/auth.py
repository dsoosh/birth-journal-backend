from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Literal

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.app.settings import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class MidwifePrincipal:
    role: Literal["midwife"]
    sub: str


@dataclass(frozen=True)
class CasePrincipal:
    role: Literal["woman"]
    case_id: str


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def mint_midwife_token(*, sub: str) -> str:
    settings = get_settings()
    now = _utcnow()
    payload = {
        "role": "midwife",
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(seconds=settings.jwt_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def mint_case_token(*, case_id: str) -> str:
    settings = get_settings()
    now = _utcnow()
    payload = {
        "role": "woman",
        "case_id": case_id,
        "iat": int(now.timestamp()),
        "exp": int((now + dt.timedelta(seconds=settings.jwt_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid_token") from exc


def require_midwife(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> MidwifePrincipal:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing_token")

    claims = _decode_token(credentials.credentials)
    if claims.get("role") != "midwife":
        raise HTTPException(status_code=403, detail="forbidden")

    sub = claims.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=401, detail="invalid_token")

    return MidwifePrincipal(role="midwife", sub=sub)


def require_case(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> CasePrincipal:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing_token")

    claims = _decode_token(credentials.credentials)
    if claims.get("role") != "woman":
        raise HTTPException(status_code=403, detail="forbidden")

    case_id = claims.get("case_id")
    if not isinstance(case_id, str) or not case_id:
        raise HTTPException(status_code=401, detail="invalid_token")

    return CasePrincipal(role="woman", case_id=case_id)
