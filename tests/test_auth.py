"""Unit tests for JWT authentication utilities."""

from __future__ import annotations

import datetime as dt
import os
import time

import pytest
import jwt

# Set required environment variables before importing
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_TTL_SECONDS", "86400")

from backend.app.auth import (
    mint_midwife_token,
    mint_case_token,
    _decode_token,
    MidwifePrincipal,
    CasePrincipal,
)
from backend.app.settings import get_settings


class TestMintMidwifeToken:
    """Test cases for mint_midwife_token function."""

    def test_returns_string(self):
        token = mint_midwife_token(sub="midwife-123")
        assert isinstance(token, str)

    def test_token_is_valid_jwt(self):
        token = mint_midwife_token(sub="midwife-456")
        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["role"] == "midwife"
        assert payload["sub"] == "midwife-456"

    def test_token_has_expiration(self):
        token = mint_midwife_token(sub="midwife-789")
        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert "exp" in payload
        assert "iat" in payload
        # Check expiration is in the future
        assert payload["exp"] > time.time()

    def test_different_subjects_different_tokens(self):
        token1 = mint_midwife_token(sub="midwife-1")
        token2 = mint_midwife_token(sub="midwife-2")
        assert token1 != token2


class TestMintCaseToken:
    """Test cases for mint_case_token function."""

    def test_returns_string(self):
        token = mint_case_token(case_id="case-123")
        assert isinstance(token, str)

    def test_token_is_valid_jwt(self):
        token = mint_case_token(case_id="case-456")
        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert payload["role"] == "woman"
        assert payload["case_id"] == "case-456"

    def test_token_has_expiration(self):
        token = mint_case_token(case_id="case-789")
        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert "exp" in payload
        assert "iat" in payload

    def test_different_case_ids_different_tokens(self):
        token1 = mint_case_token(case_id="case-1")
        token2 = mint_case_token(case_id="case-2")
        assert token1 != token2


class TestDecodeToken:
    """Test cases for _decode_token function."""

    def test_decodes_valid_midwife_token(self):
        token = mint_midwife_token(sub="test-midwife")
        payload = _decode_token(token)
        assert payload["role"] == "midwife"
        assert payload["sub"] == "test-midwife"

    def test_decodes_valid_case_token(self):
        token = mint_case_token(case_id="test-case")
        payload = _decode_token(token)
        assert payload["role"] == "woman"
        assert payload["case_id"] == "test-case"

    def test_invalid_token_raises_http_exception(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "invalid_token"

    def test_wrong_secret_raises_http_exception(self):
        from fastapi import HTTPException
        # Create token with different secret
        wrong_token = jwt.encode(
            {"role": "midwife", "sub": "test"},
            "wrong-secret",
            algorithm="HS256"
        )
        with pytest.raises(HTTPException) as exc_info:
            _decode_token(wrong_token)
        assert exc_info.value.status_code == 401

    def test_expired_token_raises_http_exception(self):
        from fastapi import HTTPException
        settings = get_settings()
        # Create an already expired token
        expired_payload = {
            "role": "midwife",
            "sub": "test",
            "exp": int(time.time()) - 3600,  # 1 hour ago
            "iat": int(time.time()) - 7200,
        }
        expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(HTTPException) as exc_info:
            _decode_token(expired_token)
        assert exc_info.value.status_code == 401


class TestMidwifePrincipal:
    """Test cases for MidwifePrincipal dataclass."""

    def test_creation(self):
        principal = MidwifePrincipal(role="midwife", sub="midwife-123")
        assert principal.role == "midwife"
        assert principal.sub == "midwife-123"

    def test_frozen(self):
        """Principal should be immutable."""
        principal = MidwifePrincipal(role="midwife", sub="midwife-123")
        with pytest.raises(AttributeError):
            principal.sub = "other"


class TestCasePrincipal:
    """Test cases for CasePrincipal dataclass."""

    def test_creation(self):
        principal = CasePrincipal(role="woman", case_id="case-123")
        assert principal.role == "woman"
        assert principal.case_id == "case-123"

    def test_frozen(self):
        """Principal should be immutable."""
        principal = CasePrincipal(role="woman", case_id="case-123")
        with pytest.raises(AttributeError):
            principal.case_id = "other"
