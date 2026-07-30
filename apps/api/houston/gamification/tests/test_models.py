from __future__ import annotations

import pytest
from django.db import IntegrityError
from django.utils import timezone

from houston.gamification.constants import CURRENT_RULE_VERSION
from houston.gamification.models import GamificationSeason, PointTransaction
from houston.gamification.services import open_season
from houston.gamification.tests.conftest import aware_local

pytestmark = pytest.mark.django_db


def test_season_starts_before_ends_constraint(paris_establishment):
    starts = aware_local("Europe/Paris", 2026, 7, 1)
    with pytest.raises(IntegrityError):
        GamificationSeason.objects.create(
            establishment=paris_establishment,
            starts_at=starts,
            ends_at=starts,
            timezone="Europe/Paris",
            rule_version=CURRENT_RULE_VERSION,
            status=GamificationSeason.Status.ACTIVE,
            closed_at=None,
        )


def test_season_active_requires_null_closed_at(paris_establishment):
    starts = aware_local("Europe/Paris", 2026, 7, 1)
    ends = aware_local("Europe/Paris", 2026, 8, 1)
    with pytest.raises(IntegrityError):
        GamificationSeason.objects.create(
            establishment=paris_establishment,
            starts_at=starts,
            ends_at=ends,
            timezone="Europe/Paris",
            rule_version=CURRENT_RULE_VERSION,
            status=GamificationSeason.Status.ACTIVE,
            closed_at=timezone.now(),
        )


def test_season_closed_requires_closed_at(paris_establishment):
    starts = aware_local("Europe/Paris", 2026, 7, 1)
    ends = aware_local("Europe/Paris", 2026, 8, 1)
    with pytest.raises(IntegrityError):
        GamificationSeason.objects.create(
            establishment=paris_establishment,
            starts_at=starts,
            ends_at=ends,
            timezone="Europe/Paris",
            rule_version=CURRENT_RULE_VERSION,
            status=GamificationSeason.Status.CLOSED,
            closed_at=None,
        )


def test_one_active_season_per_establishment(paris_establishment):
    open_season(paris_establishment, month_start_local=aware_local("Europe/Paris", 2026, 7, 1))
    with pytest.raises(IntegrityError):
        GamificationSeason.objects.create(
            establishment=paris_establishment,
            starts_at=aware_local("Europe/Paris", 2026, 8, 1),
            ends_at=aware_local("Europe/Paris", 2026, 9, 1),
            timezone="Europe/Paris",
            rule_version=CURRENT_RULE_VERSION,
            status=GamificationSeason.Status.ACTIVE,
            closed_at=None,
        )


def test_point_transaction_delta_nonzero(paris_membership, paris_establishment):
    season = open_season(
        paris_establishment,
        month_start_local=aware_local("Europe/Paris", 2026, 7, 1),
    )
    with pytest.raises(IntegrityError):
        PointTransaction.objects.create(
            membership=paris_membership,
            establishment=paris_establishment,
            season=season,
            delta=0,
            reason_code="test",
            source_type="test",
            source_id="1",
            rule_version=CURRENT_RULE_VERSION,
            occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
            idempotency_key="key-delta-zero",
        )


def test_point_transaction_idempotency_nonempty(paris_membership, paris_establishment):
    season = open_season(
        paris_establishment,
        month_start_local=aware_local("Europe/Paris", 2026, 7, 1),
    )
    with pytest.raises(IntegrityError):
        PointTransaction.objects.create(
            membership=paris_membership,
            establishment=paris_establishment,
            season=season,
            delta=1,
            reason_code="test",
            source_type="test",
            source_id="1",
            rule_version=CURRENT_RULE_VERSION,
            occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
            idempotency_key="",
        )


def test_point_transaction_idempotency_unique(paris_membership, paris_establishment):
    season = open_season(
        paris_establishment,
        month_start_local=aware_local("Europe/Paris", 2026, 7, 1),
    )
    kwargs = dict(
        membership=paris_membership,
        establishment=paris_establishment,
        season=season,
        delta=1,
        reason_code="test",
        source_type="test",
        source_id="1",
        rule_version=CURRENT_RULE_VERSION,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
        idempotency_key="same-key",
    )
    PointTransaction.objects.create(**kwargs)
    with pytest.raises(IntegrityError):
        PointTransaction.objects.create(**kwargs)
