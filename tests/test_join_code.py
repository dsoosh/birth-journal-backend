"""Unit tests for join code generation and hashing."""

from __future__ import annotations

import os
import pytest

# Set required environment variables before importing
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_TTL_SECONDS", "86400")

from backend.app.join_code import generate_join_code, hash_join_code, _ALPHABET


class TestGenerateJoinCode:
    """Test cases for generate_join_code function."""

    def test_default_length_is_six(self):
        code = generate_join_code()
        assert len(code) == 6

    def test_custom_length(self):
        code = generate_join_code(length=8)
        assert len(code) == 8

    def test_only_allowed_characters(self):
        """Join codes should only contain alphanumeric chars without ambiguous ones."""
        for _ in range(100):  # Generate many codes to test randomness
            code = generate_join_code()
            for char in code:
                assert char in _ALPHABET

    def test_codes_are_unique(self):
        """Multiple generated codes should be different (with high probability)."""
        codes = [generate_join_code() for _ in range(100)]
        unique_codes = set(codes)
        # Allow some collisions but expect mostly unique
        assert len(unique_codes) > 95

    def test_zero_length_returns_empty(self):
        code = generate_join_code(length=0)
        assert code == ""

    def test_alphabet_excludes_ambiguous_chars(self):
        """Alphabet should not contain O, 0, I, 1 which are easily confused."""
        assert 'O' not in _ALPHABET  # Ambiguous with 0
        assert '0' not in _ALPHABET  # Ambiguous with O
        assert 'I' not in _ALPHABET  # Ambiguous with 1 and l
        assert '1' not in _ALPHABET  # Ambiguous with I and l
        # Note: L is kept (only lowercase l is ambiguous)


class TestHashJoinCode:
    """Test cases for hash_join_code function."""

    def test_returns_hex_string(self):
        hash_value = hash_join_code("ABC123")
        assert isinstance(hash_value, str)
        # SHA256 produces 64 hex characters
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_same_input_same_output(self):
        """Hashing is deterministic."""
        hash1 = hash_join_code("TEST01")
        hash2 = hash_join_code("TEST01")
        assert hash1 == hash2

    def test_different_input_different_output(self):
        hash1 = hash_join_code("ABC123")
        hash2 = hash_join_code("XYZ789")
        assert hash1 != hash2

    def test_case_insensitive(self):
        """Join codes should be normalized to uppercase."""
        hash_upper = hash_join_code("ABC123")
        hash_lower = hash_join_code("abc123")
        hash_mixed = hash_join_code("AbC123")
        assert hash_upper == hash_lower == hash_mixed

    def test_strips_whitespace(self):
        """Whitespace should be stripped before hashing."""
        hash_clean = hash_join_code("ABC123")
        hash_spaces = hash_join_code("  ABC123  ")
        hash_tabs = hash_join_code("\tABC123\n")
        assert hash_clean == hash_spaces == hash_tabs

    def test_empty_string(self):
        """Empty string should still produce a valid hash."""
        hash_value = hash_join_code("")
        assert len(hash_value) == 64
