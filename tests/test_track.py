"""Unit tests for track derivation logic."""

from __future__ import annotations

import pytest

from backend.app.track import derive_track


class TestDeriveTrack:
    """Test cases for derive_track function."""

    def test_contraction_start_returns_labor(self):
        assert derive_track("contraction_start") == "labor"

    def test_contraction_end_returns_labor(self):
        assert derive_track("contraction_end") == "labor"

    def test_labor_event_returns_labor(self):
        assert derive_track("labor_event") == "labor"

    def test_set_labor_active_returns_labor(self):
        assert derive_track("set_labor_active") == "labor"

    def test_postpartum_checkin_returns_postpartum(self):
        assert derive_track("postpartum_checkin") == "postpartum"

    def test_set_postpartum_active_returns_postpartum(self):
        assert derive_track("set_postpartum_active") == "postpartum"

    def test_alert_triggered_returns_meta(self):
        assert derive_track("alert_triggered") == "meta"

    def test_alert_ack_returns_meta(self):
        assert derive_track("alert_ack") == "meta"

    def test_alert_resolve_returns_meta(self):
        assert derive_track("alert_resolve") == "meta"

    def test_note_returns_meta(self):
        assert derive_track("note") == "meta"

    def test_visit_task_returns_meta(self):
        assert derive_track("visit_task") == "meta"

    def test_midwife_reaction_returns_meta(self):
        assert derive_track("midwife_reaction") == "meta"

    def test_unknown_event_returns_meta(self):
        assert derive_track("unknown_event_type") == "meta"

    def test_empty_string_returns_meta(self):
        assert derive_track("") == "meta"

    def test_contraction_prefix_matches_any_suffix(self):
        assert derive_track("contraction_anything") == "labor"

    def test_alert_prefix_matches_any_suffix(self):
        assert derive_track("alert_custom") == "meta"
