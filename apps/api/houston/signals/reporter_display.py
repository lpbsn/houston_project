from __future__ import annotations

from houston.accounts.models import User
from houston.signals.models import Signal


def format_reporter_display_name(user: User) -> str | None:
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    if first and last:
        return f"{first} {last[0]}."

    full_name = user.get_full_name().strip()
    if not full_name:
        return None

    parts = full_name.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1][0]}."
    return full_name


def reporter_display_name_for_signal(signal: Signal) -> str | None:
    link = _oldest_source_observation_link(signal)
    if link is None:
        return None
    user = link.observation.submitted_by_membership.user
    return format_reporter_display_name(user)


def _oldest_source_observation_link(signal: Signal):
    prefetched = getattr(signal, "source_links_by_observation_chronology", None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None

    return (
        signal.source_observation_links.select_related(
            "observation__submitted_by_membership__user",
        )
        .order_by("observation__created_at", "observation__id")
        .first()
    )
