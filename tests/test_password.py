"""Unit tests for password hashing utilities."""

from __future__ import annotations

import pytest

from backend.app.password import hash_password, verify_password


class TestHashPassword:
    """Test cases for hash_password function."""

    def test_returns_string(self):
        hashed = hash_password("mypassword")
        assert isinstance(hashed, str)

    def test_bcrypt_format(self):
        """Bcrypt hashes start with $2b$."""
        hashed = hash_password("testpassword")
        assert hashed.startswith("$2b$")

    def test_different_passwords_different_hashes(self):
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        assert hash1 != hash2

    def test_same_password_different_salts(self):
        """Same password should produce different hashes due to random salt."""
        hash1 = hash_password("samepassword")
        hash2 = hash_password("samepassword")
        assert hash1 != hash2

    def test_empty_password(self):
        """Empty password should still hash successfully."""
        hashed = hash_password("")
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")

    def test_long_password(self):
        """Bcrypt truncates at 72 bytes but should still work."""
        long_pass = "a" * 100
        hashed = hash_password(long_pass)
        assert isinstance(hashed, str)

    def test_unicode_password(self):
        """Unicode passwords should work."""
        hashed = hash_password("hasło123zażółćgęślą")
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")


class TestVerifyPassword:
    """Test cases for verify_password function."""

    def test_correct_password_returns_true(self):
        password = "correctpassword"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_incorrect_password_returns_false(self):
        password = "correctpassword"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_verification(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False

    def test_case_sensitive(self):
        """Passwords should be case-sensitive."""
        password = "MyPassword"
        hashed = hash_password(password)
        assert verify_password("MyPassword", hashed) is True
        assert verify_password("mypassword", hashed) is False
        assert verify_password("MYPASSWORD", hashed) is False

    def test_unicode_verification(self):
        password = "hasło123"
        hashed = hash_password(password)
        assert verify_password("hasło123", hashed) is True
        assert verify_password("haslo123", hashed) is False

    def test_whitespace_matters(self):
        password = "password with spaces"
        hashed = hash_password(password)
        assert verify_password("password with spaces", hashed) is True
        assert verify_password("passwordwithspaces", hashed) is False
        assert verify_password(" password with spaces ", hashed) is False
