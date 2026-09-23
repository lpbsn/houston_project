from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from typing import Any
from uuid import UUID

from django.db import IntegrityError, transaction

from houston.establishments.mama_nice_dataset_exceptions import (
    MamaNiceDatasetError,
    MamaNiceSeedTargetDivergedError,
    MamaNiceSeedTargetMissingError,
    MamaNiceSeedTargetUntrackedError,
)
from houston.establishments.models import Establishment, MamaNiceSeedRecord


def canonical_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _get_record(
    *,
    establishment: Establishment,
    object_type: str,
    seed_key: str,
) -> MamaNiceSeedRecord | None:
    return MamaNiceSeedRecord.objects.filter(
        establishment=establishment,
        object_type=object_type,
        seed_key=seed_key,
    ).first()


def apply_seed_event(
    *,
    establishment: Establishment,
    object_type: str,
    seed_key: str,
    event_kind: str,
    event_at: datetime,
    fingerprint_payload: dict[str, Any],
    resume: bool,
    target_exists: Callable[[UUID], bool],
    writer: Callable[[], UUID],
    natural_identity_exists: Callable[[], bool] | None = None,
) -> str:
    fingerprint = canonical_fingerprint(fingerprint_payload)
    record = _get_record(
        establishment=establishment,
        object_type=object_type,
        seed_key=seed_key,
    )
    if record is None:
        if natural_identity_exists is not None and natural_identity_exists():
            raise MamaNiceSeedTargetUntrackedError(seed_key)
        with transaction.atomic():
            object_id = writer()
            try:
                MamaNiceSeedRecord.objects.create(
                    establishment=establishment,
                    object_type=object_type,
                    seed_key=seed_key,
                    object_id=object_id,
                    fingerprint=fingerprint,
                    event_kind=event_kind,
                    event_at=event_at,
                )
            except IntegrityError as exc:
                raise MamaNiceDatasetError(
                    [f"{seed_key}: uniqueness conflict while inserting seed record"]
                ) from exc
        return "written"

    if not target_exists(record.object_id):
        raise MamaNiceSeedTargetMissingError(seed_key)
    if record.fingerprint != fingerprint:
        raise MamaNiceSeedTargetDivergedError(seed_key)
    if not resume:
        raise MamaNiceDatasetError([f"{seed_key}: already applied, use --resume"])
    return "skipped"
