from __future__ import annotations

from datetime import date

import pytest

from houston.gamification.models import GamificationSeason
from houston.gamification.services import open_season
from houston.gamification.tasks import rollover_gamification_seasons_task
from houston.testing.factories import create_establishment

pytestmark = pytest.mark.django_db


def test_rollover_task_processes_active_establishment(paris_establishment):
    open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    # Freeze "now" indirectly by ensuring season is due via direct service path in task:
    # Task uses timezone.now(); for smoke we just verify it runs and counts.
    processed = rollover_gamification_seasons_task(
        establishment_id=str(paris_establishment.id),
    )
    assert processed == 1


def test_rollover_task_all_establishments_smoke():
    a = create_establishment(name="A", timezone="Europe/Paris")
    b = create_establishment(name="B", timezone="UTC")
    open_season(a, month_start_local=date(2026, 7, 1))
    open_season(b, month_start_local=date(2026, 7, 1))
    processed = rollover_gamification_seasons_task(establishment_id=None)
    assert processed >= 2
    assert GamificationSeason.objects.filter(establishment=a).exists()
