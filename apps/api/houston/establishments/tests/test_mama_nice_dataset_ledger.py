from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from django.db import transaction

from houston.establishments.mama_nice_dataset_exceptions import (
    MamaNiceSeedTargetDivergedError,
    MamaNiceSeedTargetMissingError,
    MamaNiceSeedTargetUntrackedError,
)
from houston.establishments.mama_nice_dataset_ledger import apply_seed_event
from houston.establishments.models import MamaNiceSeedRecord
from houston.testing.factories import create_establishment

pytestmark = pytest.mark.django_db

PARIS = ZoneInfo("Europe/Paris")


def test_seed_event_writes_record_with_writer():
    establishment = create_establishment(name="Mama ledger")
    object_id = uuid4()
    status = apply_seed_event(
        establishment=establishment,
        object_type=MamaNiceSeedRecord.ObjectType.OBSERVATION,
        seed_key="obs:test",
        event_kind="observation_submit",
        event_at=datetime(2026, 9, 1, tzinfo=PARIS),
        fingerprint_payload={"n": 1},
        resume=False,
        writer=lambda: object_id,
        target_exists=lambda _object_id: True,
    )
    assert status == "written"
    assert MamaNiceSeedRecord.objects.filter(seed_key="obs:test").exists()


def test_seed_event_skips_on_resume_when_fingerprint_matches():
    establishment = create_establishment(name="Mama ledger resume")
    object_id = uuid4()
    apply_seed_event(
        establishment=establishment,
        object_type="observation",
        seed_key="obs:resume",
        event_kind="observation_submit",
        event_at=datetime(2026, 9, 1, tzinfo=PARIS),
        fingerprint_payload={"n": 1},
        resume=False,
        writer=lambda: object_id,
        target_exists=lambda _object_id: True,
    )
    status = apply_seed_event(
        establishment=establishment,
        object_type="observation",
        seed_key="obs:resume",
        event_kind="observation_submit",
        event_at=datetime(2026, 9, 1, tzinfo=PARIS),
        fingerprint_payload={"n": 1},
        resume=True,
        writer=lambda: uuid4(),
        target_exists=lambda _object_id: True,
    )
    assert status == "skipped"
    assert MamaNiceSeedRecord.objects.filter(seed_key="obs:resume").count() == 1


def test_seed_event_fails_when_target_missing():
    establishment = create_establishment(name="Mama ledger missing")
    object_id = uuid4()
    apply_seed_event(
        establishment=establishment,
        object_type="observation",
        seed_key="obs:missing",
        event_kind="observation_submit",
        event_at=datetime(2026, 9, 1, tzinfo=PARIS),
        fingerprint_payload={"n": 1},
        resume=False,
        writer=lambda: object_id,
        target_exists=lambda _object_id: True,
    )
    with pytest.raises(MamaNiceSeedTargetMissingError):
        apply_seed_event(
            establishment=establishment,
            object_type="observation",
            seed_key="obs:missing",
            event_kind="observation_submit",
            event_at=datetime(2026, 9, 1, tzinfo=PARIS),
            fingerprint_payload={"n": 1},
            resume=True,
            writer=lambda: uuid4(),
            target_exists=lambda _object_id: False,
        )


def test_seed_event_fails_when_fingerprint_diverges():
    establishment = create_establishment(name="Mama ledger diverge")
    object_id = uuid4()
    apply_seed_event(
        establishment=establishment,
        object_type="observation",
        seed_key="obs:diverge",
        event_kind="observation_submit",
        event_at=datetime(2026, 9, 1, tzinfo=PARIS),
        fingerprint_payload={"n": 1},
        resume=False,
        writer=lambda: object_id,
        target_exists=lambda _object_id: True,
    )
    with pytest.raises(MamaNiceSeedTargetDivergedError):
        apply_seed_event(
            establishment=establishment,
            object_type="observation",
            seed_key="obs:diverge",
            event_kind="observation_submit",
            event_at=datetime(2026, 9, 1, tzinfo=PARIS),
            fingerprint_payload={"n": 2},
            resume=True,
            writer=lambda: uuid4(),
            target_exists=lambda _object_id: True,
        )


def test_seed_event_fails_when_natural_identity_untracked():
    establishment = create_establishment(name="Mama ledger untracked")
    with pytest.raises(MamaNiceSeedTargetUntrackedError):
        apply_seed_event(
            establishment=establishment,
            object_type="observation",
            seed_key="obs:untracked",
            event_kind="observation_submit",
            event_at=datetime(2026, 9, 1, tzinfo=PARIS),
            fingerprint_payload={"n": 1},
            resume=False,
            writer=lambda: uuid4(),
            target_exists=lambda _object_id: True,
            natural_identity_exists=lambda: True,
        )


def test_writer_rollback_leaves_no_record():
    establishment = create_establishment(name="Mama ledger rollback")

    def writer():
        raise RuntimeError("writer failed")

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            apply_seed_event(
                establishment=establishment,
                object_type="observation",
                seed_key="obs:rollback",
                event_kind="observation_submit",
                event_at=datetime(2026, 9, 1, tzinfo=PARIS),
                fingerprint_payload={"n": 1},
                resume=False,
                writer=writer,
                target_exists=lambda _object_id: False,
            )
    assert not MamaNiceSeedRecord.objects.filter(seed_key="obs:rollback").exists()


def test_seed_event_allows_open_and_close_on_same_season_object():
    establishment = create_establishment(name="Mama ledger season pair")
    object_id = uuid4()
    apply_seed_event(
        establishment=establishment,
        object_type=MamaNiceSeedRecord.ObjectType.SEASON,
        seed_key="season:2026-03-01",
        event_kind="season_open",
        event_at=datetime(2026, 3, 1, tzinfo=PARIS),
        fingerprint_payload={"month": "2026-03-01", "action": "open"},
        resume=False,
        writer=lambda: object_id,
        target_exists=lambda _object_id: True,
    )
    status = apply_seed_event(
        establishment=establishment,
        object_type=MamaNiceSeedRecord.ObjectType.SEASON,
        seed_key="season:2026-03-01:close",
        event_kind="season_close",
        event_at=datetime(2026, 4, 1, tzinfo=PARIS),
        fingerprint_payload={"month": "2026-03-01", "action": "close"},
        resume=False,
        writer=lambda: object_id,
        target_exists=lambda _object_id: True,
    )
    assert status == "written"
    assert (
        MamaNiceSeedRecord.objects.filter(
            establishment=establishment,
            object_type=MamaNiceSeedRecord.ObjectType.SEASON,
            object_id=object_id,
        ).count()
        == 2
    )
