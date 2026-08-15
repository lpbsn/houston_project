from __future__ import annotations

import uuid

from houston.signals.models import Signal


def normalize_backfill_signal_ids(signal_ids) -> list[uuid.UUID]:
    if not signal_ids:
        return []
    return [uuid.UUID(str(signal_id)) for signal_id in signal_ids]


def select_explicit_backfill_signal_ids(
    *,
    signal_ids: list[uuid.UUID],
    scope: dict[str, str | None],
    limit: int,
) -> tuple[list[uuid.UUID], dict[str, int], str]:
    unique_ids = sorted(set(signal_ids))
    if len(unique_ids) > limit:
        raise ValueError(
            f"signal-id count must be less than or equal to the effective limit ({limit})"
        )
    scoped = _scoped_signals(scope=scope)
    signals = list(scoped.filter(id__in=unique_ids).order_by("created_at", "id"))
    found_ids = {signal.id for signal in signals}
    missing = [str(signal_id) for signal_id in unique_ids if signal_id not in found_ids]
    if missing:
        raise ValueError(
            "signal-id values were not found in the selected scope: "
            + ", ".join(sorted(missing))
        )
    merged = [str(signal.id) for signal in signals if signal.merged_into_id is not None]
    if merged:
        raise ValueError("merged signals cannot be backfilled explicitly: " + ", ".join(merged))
    return [signal.id for signal in signals], {"merged": 0}, ""


def _scoped_signals(*, scope: dict[str, str | None]):
    queryset = Signal.objects.select_related("establishment", "establishment__organization")
    if scope["organization_id"]:
        queryset = queryset.filter(establishment__organization_id=scope["organization_id"])
    if scope["establishment_id"]:
        queryset = queryset.filter(establishment_id=scope["establishment_id"])
    return queryset
