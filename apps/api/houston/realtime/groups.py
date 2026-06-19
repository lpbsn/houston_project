from __future__ import annotations

from uuid import UUID


def establishment_group_name(*, establishment_id: UUID) -> str:
    return f"realtime_est_{establishment_id}"


def membership_group_name(*, establishment_id: UUID, membership_id: UUID) -> str:
    return f"realtime_est_{establishment_id}_mbr_{membership_id}"


def session_group_name(*, session_id: UUID) -> str:
    return f"realtime_session_{session_id}"
