"""Write-once first-seen of a motif in an establishment (post-cutover)."""

from __future__ import annotations

from datetime import datetime

from houston.analytics.models import OperationalPattern, PatternEstablishmentSighting
from houston.establishments.models import Establishment


def record_pattern_establishment_sighting(
    *,
    pattern: OperationalPattern,
    establishment: Establishment,
    observed_at: datetime,
) -> PatternEstablishmentSighting:
    sighting, _created = PatternEstablishmentSighting.objects.get_or_create(
        pattern=pattern,
        establishment=establishment,
        defaults={"observed_at": observed_at},
    )
    return sighting


def merge_pattern_establishment_sightings(
    *,
    source_pattern: OperationalPattern,
    target_pattern: OperationalPattern,
) -> None:
    source_sightings = list(
        PatternEstablishmentSighting.objects.filter(pattern=source_pattern).order_by("id")
    )
    if not source_sightings:
        return

    target_by_establishment = {
        sighting.establishment_id: sighting
        for sighting in PatternEstablishmentSighting.objects.filter(pattern=target_pattern)
    }
    for sighting in source_sightings:
        existing = target_by_establishment.get(sighting.establishment_id)
        if existing is None:
            sighting.pattern = target_pattern
            sighting.save(update_fields=["pattern", "updated_at"])
            target_by_establishment[sighting.establishment_id] = sighting
            continue
        if sighting.observed_at < existing.observed_at:
            existing.observed_at = sighting.observed_at
            existing.save(update_fields=["observed_at", "updated_at"])
        sighting.delete()
