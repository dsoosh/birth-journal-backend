"""Unit tests for QR code generation."""

from __future__ import annotations

import pytest

from backend.app.qr import generate_qr_code


class TestGenerateQrCode:
    """Test cases for generate_qr_code function."""

    def test_returns_data_uri(self):
        """Should return a valid data URI string."""
        result = generate_qr_code("https://example.com")
        if result is None:
            pytest.skip("qrcode library not installed")
        assert result.startswith("data:image/png;base64,")

    def test_base64_encoded(self):
        """Data URI should contain valid base64."""
        import base64
        result = generate_qr_code("TEST123")
        if result is None:
            pytest.skip("qrcode library not installed")
        # Extract base64 part
        base64_part = result.split(",")[1]
        # Should decode without error
        decoded = base64.b64decode(base64_part)
        # Should be PNG (starts with PNG magic bytes)
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'

    def test_different_data_different_output(self):
        """Different inputs should produce different QR codes."""
        result1 = generate_qr_code("DATA1")
        result2 = generate_qr_code("DATA2")
        if result1 is None or result2 is None:
            pytest.skip("qrcode library not installed")
        assert result1 != result2

    def test_same_data_same_output(self):
        """Same input should produce same QR code."""
        result1 = generate_qr_code("SAME")
        result2 = generate_qr_code("SAME")
        if result1 is None or result2 is None:
            pytest.skip("qrcode library not installed")
        assert result1 == result2

    def test_empty_string(self):
        """Empty string should still produce a QR code."""
        result = generate_qr_code("")
        if result is None:
            pytest.skip("qrcode library not installed")
        assert result.startswith("data:image/png;base64,")

    def test_unicode_data(self):
        """Unicode data should be encoded properly."""
        result = generate_qr_code("Zażółć gęślą jaźń")
        if result is None:
            pytest.skip("qrcode library not installed")
        assert result.startswith("data:image/png;base64,")

    def test_long_data(self):
        """Long data should still produce a QR code."""
        long_data = "A" * 500
        result = generate_qr_code(long_data)
        if result is None:
            pytest.skip("qrcode library not installed")
        assert result.startswith("data:image/png;base64,")
