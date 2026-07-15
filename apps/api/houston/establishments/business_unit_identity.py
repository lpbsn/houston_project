from __future__ import annotations

from typing import Protocol
from uuid import UUID

from houston.establishments.taxonomy_normalization import slugify_label


class ActivitySubjectEstablishmentDerivation(Protocol):
    establishment_id: UUID | None
    business_unit: object


def normalize_business_unit_specific_name(specific_name: str) -> str:
    return slugify_label(specific_name)


def build_business_unit_routing_key(
    *,
    business_unit_id: UUID,
    catalog_key: str,
    specific_name: str,
) -> str:
    specific_slug = slugify_label(specific_name).replace("_", "-")[:48]
    return f"{catalog_key}--{specific_slug}--{business_unit_id.hex[:16]}"


def derive_activity_subject_establishment(
    activity_subject: ActivitySubjectEstablishmentDerivation,
) -> None:
    activity_subject.establishment_id = activity_subject.business_unit.establishment_id
