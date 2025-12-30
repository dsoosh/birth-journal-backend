from __future__ import annotations

import hashlib
import secrets

from backend.app.settings import get_settings

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_join_code(length: int = 6) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def hash_join_code(join_code: str) -> str:
    settings = get_settings()
    normalized = join_code.strip().upper()
    digest = hashlib.sha256(f"{settings.jwt_secret}:{normalized}".encode("utf-8")).hexdigest()
    return digest
