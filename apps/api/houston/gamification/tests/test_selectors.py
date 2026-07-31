from __future__ import annotations

import uuid
from datetime import date

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import (
    BADGE_CODE_BRONZE,
    BADGE_CODE_GOLD,
    BADGE_CODE_SILVER,
    REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
    REASON_EXECUTION_REVIEWED,
    REASON_RECURRING_EXECUTION_DONE,
    REASON_RESOLUTION_REQUEST_APPROVED,
    REASON_SIGNAL_MOVED_IN_PROGRESS,
    REASON_SIGNAL_RESOLVED,
    UNKNOWN_REASON_LABEL,
)
from houston.gamification.models import GamificationSeason
from houston.gamification.selectors import (
    current_gamification_summary,
    gamification_rules_payload,
    grade_progress_payload,
    list_personal_gamification_seasons,
    point_delta_by_membership_id_for_source,
    reason_label,
)
from houston.gamification.services import award_points, close_season, open_season
from houston.gamification.tests.conftest import aware_local
from houston.testing.factories import create_establishment, create_membership

pytestmark = pytest.mark.django_db


def _award(
    *,
    membership,
    establishment,
    occurred_at,
    delta,
    reason_code="test.award",
    source_id=None,
    idempotency_key=None,
):
    sid = source_id or str(uuid.uuid4())
    return award_points(
        membership=membership,
        establishment=establishment,
        delta=delta,
        reason_code=reason_code,
        source_type="test",
        source_id=sid,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key or f"{reason_code}:{sid}:{membership.id}",
    )


@pytest.mark.parametrize(
    ("score", "grade", "next_grade", "next_threshold", "points_to_next", "is_max"),
    [
        (29, None, BADGE_CODE_BRONZE, 30, 1, False),
        (30, BADGE_CODE_BRONZE, BADGE_CODE_SILVER, 50, 20, False),
        (49, BADGE_CODE_BRONZE, BADGE_CODE_SILVER, 50, 1, False),
        (50, BADGE_CODE_SILVER, BADGE_CODE_GOLD, 70, 20, False),
        (69, BADGE_CODE_SILVER, BADGE_CODE_GOLD, 70, 1, False),
        (70, BADGE_CODE_GOLD, None, None, 0, True),
    ],
)
def test_grade_progress_thresholds(
    score,
    grade,
    next_grade,
    next_threshold,
    points_to_next,
    is_max,
):
    payload = grade_progress_payload(score)

    assert payload["grade"] == grade
    assert payload["next_grade"] == next_grade
    assert payload["next_grade_threshold"] == next_threshold
    assert payload["points_to_next_grade"] == points_to_next
    assert payload["is_max_grade"] is is_max


def test_progress_ratio_is_score_divided_by_next_threshold():
    payload = grade_progress_payload(47)

    assert payload["next_grade"] == BADGE_CODE_SILVER
    assert payload["next_grade_threshold"] == 50
    assert payload["progress_ratio"] == 0.94


def test_current_summary_sums_positive_and_negative_transactions(
    paris_membership,
    paris_establishment,
):
    open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 5, 12),
        delta=50,
        idempotency_key="positive",
    )
    _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 6, 12),
        delta=-3,
        idempotency_key="negative",
    )

    payload = current_gamification_summary(
        membership=paris_membership,
        establishment=paris_establishment,
        now=aware_local("Europe/Paris", 2026, 7, 20, 12),
    )

    assert payload["score"] == 47
    assert payload["grade"] == BADGE_CODE_BRONZE
    assert payload["next_grade"] == BADGE_CODE_SILVER
    assert payload["points_to_next_grade"] == 3
    assert payload["progress_ratio"] == 0.94


def test_current_summary_without_persisted_season_does_not_mutate(
    paris_membership,
    paris_establishment,
):
    before = GamificationSeason.objects.count()

    payload = current_gamification_summary(
        membership=paris_membership,
        establishment=paris_establishment,
        now=aware_local("Europe/Paris", 2026, 7, 20, 12),
    )

    assert payload["season_id"] is None
    assert payload["score"] == 0
    assert payload["grade"] is None
    assert payload["next_grade"] == BADGE_CODE_BRONZE
    assert GamificationSeason.objects.count() == before


def test_closed_season_under_bronze_has_no_final_grade(
    paris_membership,
    paris_establishment,
):
    season = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 5, 12),
        delta=29,
        idempotency_key="under-bronze",
    )
    close_season(season, closed_at=aware_local("Europe/Paris", 2026, 8, 1))

    seasons = list_personal_gamification_seasons(
        membership=paris_membership,
        establishment=paris_establishment,
        now=aware_local("Europe/Paris", 2026, 7, 20, 12),
    )

    closed = next(item for item in seasons if item["season_id"] == season.id)
    assert closed["score"] == 29
    assert closed["grade"] is None


def test_reason_labels_cover_gam02_to_gam06_and_unknown_fallback():
    expected_codes = {
        REASON_SIGNAL_MOVED_IN_PROGRESS,
        REASON_SIGNAL_RESOLVED,
        REASON_RESOLUTION_REQUEST_APPROVED,
        REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
        REASON_RECURRING_EXECUTION_DONE,
        REASON_EXECUTION_REVIEWED,
    }
    rules = gamification_rules_payload()
    rule_codes = {rule["code"] for rule in rules["points"]}

    assert expected_codes <= rule_codes
    assert "signal.marked_interesting" not in rule_codes
    for code in expected_codes:
        assert reason_label(code) != UNKNOWN_REASON_LABEL
    assert reason_label("future.unknown") == UNKNOWN_REASON_LABEL


def test_point_delta_by_membership_id_for_source_matches_exact_source_only():
    establishment = create_establishment(name="Exact Source Hotel", timezone="UTC")
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    target_source_id = uuid.uuid4()
    other_source_id = uuid.uuid4()
    open_season(establishment, month_start_local=date(2026, 7, 1))
    _award(
        membership=membership,
        establishment=establishment,
        occurred_at=aware_local("UTC", 2026, 7, 5, 12),
        delta=2,
        reason_code=REASON_SIGNAL_RESOLVED,
        source_id=target_source_id,
        idempotency_key="exact-target",
    )
    _award(
        membership=membership,
        establishment=establishment,
        occurred_at=aware_local("UTC", 2026, 7, 5, 12),
        delta=2,
        reason_code=REASON_SIGNAL_RESOLVED,
        source_id=other_source_id,
        idempotency_key="exact-other",
    )

    delta_by_membership_id = point_delta_by_membership_id_for_source(
        reason_code=REASON_SIGNAL_RESOLVED,
        source_type="test",
        source_id=target_source_id,
        membership_ids={membership.id},
    )

    assert delta_by_membership_id == {membership.id: 2}
