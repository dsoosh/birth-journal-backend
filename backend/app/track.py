from __future__ import annotations

from typing import Literal

Track = Literal["labor", "postpartum", "meta"]


def derive_track(event_type: str) -> Track:
    if event_type.startswith("contraction_"):
        return "labor"

    if event_type in {"labor_event", "set_labor_active"}:
        return "labor"

    if event_type in {"postpartum_checkin", "set_postpartum_active"}:
        return "postpartum"

    if event_type.startswith("alert_"):
        return "meta"

    if event_type in {"note", "visit_task"}:
        return "meta"

    return "meta"
