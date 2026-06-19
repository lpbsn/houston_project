from __future__ import annotations

from houston.accounts.models import User
from houston.signals.models import Signal, SignalSourceObservation


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
    link = created_from_source_observation_link(signal)
    if link is None:
        return None
    user = link.observation.submitted_by_membership.user
    return format_reporter_display_name(user)


def media_count_for_signal(signal: Signal) -> int:
    link = created_from_source_observation_link(signal)
    if link is None:
        return 0
    return observation_media_count(link.observation)


def observation_media_count(observation) -> int:
    prefetched = getattr(observation, "_prefetched_objects_cache", None)
    if prefetched is not None and "media_items" in prefetched:
        return len(prefetched["media_items"])
    return observation.media_items.count()


def created_from_source_observation_link(signal: Signal):
    prefetched = getattr(signal, "created_from_source_links", None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None

    return (
        signal.source_observation_links.filter(
            link_type=SignalSourceObservation.LinkType.CREATED_FROM,
        )
        .select_related(
            "observation__submitted_by_membership__user",
        )
        .order_by("observation__created_at", "observation__id")
        .first()
    )


def created_from_observation_media_items(signal: Signal):
    link = created_from_source_observation_link(signal)
    if link is None:
        return []
    observation = link.observation
    prefetched = getattr(observation, "_prefetched_objects_cache", None)
    if prefetched is not None and "media_items" in prefetched:
        return sorted(prefetched["media_items"], key=lambda item: item.position)
    return list(observation.media_items.order_by("position"))


def oldest_source_observation_link(signal: Signal):
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
