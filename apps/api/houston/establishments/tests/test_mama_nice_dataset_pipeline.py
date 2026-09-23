from __future__ import annotations

import pytest
from django.conf import settings
from django.test import override_settings

from houston.action_plans.models import ActionPlanExecution, ActionPlanSchedule
from houston.establishments.mama_nice_dataset_acceptance import validate_mama_nice_dataset
from houston.establishments.mama_nice_dataset_bootstrap import bootstrap_mama_nice_dataset
from houston.establishments.mama_nice_dataset_clock import (
    REFERENCE_SEED_KEY,
    load_persisted_reference_at,
)
from houston.establishments.mama_nice_dataset_constants import (
    LOCAL_ESTABLISHMENT_NAME,
    LOCAL_ORG_NAME,
    OBJECT_TYPE_CLOCK,
    OWNER_PASSWORD_ENV,
    PERSONA_PASSWORD_ENV,
    SNAPSHOT,
)
from houston.establishments.mama_nice_dataset_replay import seed_mama_nice_dataset
from houston.establishments.models import Establishment, MamaNiceSeedRecord
from houston.observations.models import Observation
from houston.signals.models import Signal
from houston.testing.factories import TEST_PASSWORD

pytestmark = [pytest.mark.django_db, pytest.mark.heavy]


def _corpus_counts(establishment: Establishment) -> dict[str, int]:
    return {
        "observations": Observation.objects.filter(establishment=establishment).count(),
        "signals": Signal.objects.filter(establishment=establishment).count(),
        "executions": ActionPlanExecution.objects.filter(establishment=establishment).count(),
        "schedules": ActionPlanSchedule.objects.filter(establishment=establishment).count(),
    }


@override_settings(DEBUG=True)
def test_mama_nice_full_seed_acceptance_and_resume(imported_catalog, monkeypatch):
    del imported_catalog
    database_name = str(settings.DATABASES["default"]["NAME"])
    assert database_name.startswith("test_")
    monkeypatch.setenv(OWNER_PASSWORD_ENV, TEST_PASSWORD)
    monkeypatch.setenv(PERSONA_PASSWORD_ENV, TEST_PASSWORD)

    bootstrap_mama_nice_dataset(confirm=True)
    first = seed_mama_nice_dataset(
        establishment_id=None,
        dry_run=False,
        confirm=True,
        resume=False,
        local=True,
        as_of=SNAPSHOT,
    )
    establishment = Establishment.objects.get(
        name=LOCAL_ESTABLISHMENT_NAME,
        organization__name=LOCAL_ORG_NAME,
    )
    errors = validate_mama_nice_dataset(establishment=establishment)
    assert errors == [], "\n".join(errors)
    counts = _corpus_counts(establishment)

    clock = MamaNiceSeedRecord.objects.get(
        establishment=establishment,
        object_type=OBJECT_TYPE_CLOCK,
        seed_key=REFERENCE_SEED_KEY,
    )
    assert load_persisted_reference_at(establishment) == SNAPSHOT
    assert clock.event_at.astimezone(SNAPSHOT.tzinfo) == SNAPSHOT
    first_fingerprint = clock.fingerprint

    resumed = seed_mama_nice_dataset(
        establishment_id=None,
        dry_run=False,
        confirm=True,
        resume=True,
        local=True,
        as_of=SNAPSHOT,
    )
    assert resumed.written == 0
    assert resumed.skipped == first.written
    assert _corpus_counts(establishment) == counts
    clock.refresh_from_db()
    assert clock.fingerprint == first_fingerprint
    assert load_persisted_reference_at(establishment) == SNAPSHOT
    errors = validate_mama_nice_dataset(establishment=establishment)
    assert errors == [], "\n".join(errors)
