from __future__ import annotations

import uuid
from datetime import date
from datetime import timezone as dt_timezone

import pytest

from houston.gamification.constants import (
    BADGE_CODE_BRONZE,
    BADGE_CODE_GOLD,
    BADGE_CODE_SILVER,
    build_idempotency_key,
)
from houston.gamification.exceptions import (
    GamificationIdempotencyConflictError,
    GamificationSeasonClosedError,
    GamificationValidationError,
)
from houston.gamification.models import BadgeAward, GamificationSeason, PointTransaction
from houston.gamification.selectors import (
    get_active_season,
    month_bounds_for_occurred_at,
    sum_points_for_membership_season,
)
from houston.gamification.services import (
    award_points,
    close_season,
    ensure_season_for_occurred_at,
    open_season,
    rollover_establishment_if_due,
)
from houston.gamification.tests.conftest import aware_local
from houston.testing.factories import create_establishment, create_membership

pytestmark = pytest.mark.django_db


def _award(
    *,
    membership,
    establishment,
    occurred_at,
    delta=1,
    reason_code="test.award",
    source_id=None,
    idempotency_key=None,
    source_event_id="",
):
    sid = source_id or str(uuid.uuid4())
    key = idempotency_key or build_idempotency_key(
        reason_code=reason_code,
        subject_id=sid,
        membership_id=membership.id,
    )
    return award_points(
        membership=membership,
        establishment=establishment,
        delta=delta,
        reason_code=reason_code,
        source_type="test",
        source_id=sid,
        source_event_id=source_event_id,
        occurred_at=occurred_at,
        idempotency_key=key,
    )


def test_open_close_freezes_badges(paris_membership, paris_establishment):
    season = open_season(
        paris_establishment,
        month_start_local=date(2026, 7, 1),
    )
    _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 10, 12),
        delta=30,
        idempotency_key="badge-bronze",
        source_id="b1",
    )
    other = create_membership(establishment=paris_establishment)
    _award(
        membership=other,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 11, 12),
        delta=50,
        idempotency_key="badge-silver",
        source_id="s1",
    )
    gold_member = create_membership(establishment=paris_establishment)
    _award(
        membership=gold_member,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 12, 12),
        delta=70,
        idempotency_key="badge-gold",
        source_id="g1",
    )
    low = create_membership(establishment=paris_establishment)
    _award(
        membership=low,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 13, 12),
        delta=10,
        idempotency_key="badge-none",
        source_id="n1",
    )

    closed = close_season(season, closed_at=aware_local("Europe/Paris", 2026, 8, 1))
    assert closed.status == GamificationSeason.Status.CLOSED
    assert closed.closed_at is not None

    awards = {a.membership_id: a for a in BadgeAward.objects.filter(season=closed)}
    assert awards[paris_membership.id].badge_code == BADGE_CODE_BRONZE
    assert awards[other.id].badge_code == BADGE_CODE_SILVER
    assert awards[gold_member.id].badge_code == BADGE_CODE_GOLD
    assert low.id not in awards
    assert PointTransaction.objects.filter(season=closed).count() == 4


def test_award_idempotent_same_payload(paris_membership, paris_establishment):
    occurred_at = aware_local("Europe/Paris", 2026, 7, 15, 12)
    first = _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=occurred_at,
        delta=2,
        idempotency_key="idem-same",
        source_id="subj-1",
        source_event_id="evt-1",
    )
    second = _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=occurred_at,
        delta=2,
        idempotency_key="idem-same",
        source_id="subj-1",
        source_event_id="evt-1",
    )
    assert second.id == first.id
    assert PointTransaction.objects.filter(idempotency_key="idem-same").count() == 1


def test_award_idempotent_payload_conflict(paris_membership, paris_establishment):
    occurred_at = aware_local("Europe/Paris", 2026, 7, 15, 12)
    _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=occurred_at,
        delta=2,
        idempotency_key="idem-conflict",
        source_id="subj-1",
    )
    with pytest.raises(GamificationIdempotencyConflictError):
        _award(
            membership=paris_membership,
            establishment=paris_establishment,
            occurred_at=occurred_at,
            delta=3,
            idempotency_key="idem-conflict",
            source_id="subj-1",
        )
    assert PointTransaction.objects.filter(idempotency_key="idem-conflict").count() == 1


def test_award_rejects_closed_season(paris_membership, paris_establishment):
    season = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    close_season(season, closed_at=aware_local("Europe/Paris", 2026, 8, 1))
    with pytest.raises(GamificationSeasonClosedError):
        _award(
            membership=paris_membership,
            establishment=paris_establishment,
            occurred_at=aware_local("Europe/Paris", 2026, 7, 20, 12),
            idempotency_key="closed-reject",
            source_id="c1",
        )
    # ensure does not reopen
    season.refresh_from_db()
    assert season.status == GamificationSeason.Status.CLOSED
    assert get_active_season(paris_establishment) is None


def test_award_before_beat_rolls_month(paris_membership, paris_establishment):
    july = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 31, 23),
        delta=5,
        idempotency_key="july-last",
        source_id="j1",
    )

    august_award = _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 8, 1, 0, 1),
        delta=3,
        idempotency_key="aug-first",
        source_id="a1",
    )

    july.refresh_from_db()
    assert july.status == GamificationSeason.Status.CLOSED
    active = get_active_season(paris_establishment)
    assert active is not None
    assert active.starts_at == aware_local("Europe/Paris", 2026, 8, 1)
    assert august_award.season_id == active.id
    assert sum_points_for_membership_season(paris_membership, active) == 3
    assert sum_points_for_membership_season(paris_membership, july) == 5


def test_logical_concurrency_award_then_close(paris_membership, paris_establishment):
    season = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    tx = _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
        delta=40,
        idempotency_key="before-close",
        source_id="bc1",
    )
    closed = close_season(season, closed_at=aware_local("Europe/Paris", 2026, 8, 1))
    assert tx.season_id == closed.id
    award = BadgeAward.objects.get(membership=paris_membership, season=closed)
    assert award.points_total == 40
    assert award.badge_code == BADGE_CODE_BRONZE


def test_logical_concurrency_close_then_award(paris_membership, paris_establishment):
    season = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    close_season(season, closed_at=aware_local("Europe/Paris", 2026, 8, 1))
    with pytest.raises(GamificationSeasonClosedError):
        _award(
            membership=paris_membership,
            establishment=paris_establishment,
            occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
            idempotency_key="after-close",
            source_id="ac1",
        )
    assert not PointTransaction.objects.filter(idempotency_key="after-close").exists()


def test_cross_establishment_rejected(paris_membership, paris_establishment):
    other_establishment = create_establishment(name="Other", timezone="Europe/Paris")
    open_season(other_establishment, month_start_local=date(2026, 7, 1))
    with pytest.raises(GamificationValidationError) as exc_info:
        award_points(
            membership=paris_membership,
            establishment=other_establishment,
            delta=1,
            reason_code="test.award",
            source_type="test",
            source_id="x1",
            occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
            idempotency_key="cross-estab",
        )
    assert exc_info.value.code == "gamification_cross_establishment"


def test_dst_spring_forward_month_bounds(paris_establishment):
    # Europe/Paris DST starts 2026-03-29; March season must still be contiguous.
    starts, ends = month_bounds_for_occurred_at(
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 3, 15, 12),
    )
    assert starts == aware_local("Europe/Paris", 2026, 3, 1)
    assert ends == aware_local("Europe/Paris", 2026, 4, 1)
    assert starts.utcoffset() != ends.utcoffset()  # CET vs CEST

    season = ensure_season_for_occurred_at(
        paris_establishment,
        aware_local("Europe/Paris", 2026, 3, 29, 3, 30),
    )
    assert season.starts_at == starts
    assert season.ends_at == ends

    just_before_april = aware_local("Europe/Paris", 2026, 3, 31, 23, 59)
    assert season.starts_at <= just_before_april < season.ends_at


def test_dst_fall_back_month_bounds(paris_establishment):
    starts, ends = month_bounds_for_occurred_at(
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 10, 15, 12),
    )
    assert starts == aware_local("Europe/Paris", 2026, 10, 1)
    assert ends == aware_local("Europe/Paris", 2026, 11, 1)
    season = open_season(paris_establishment, month_start_local=date(2026, 10, 1))
    assert season.starts_at == starts
    assert season.ends_at == ends


def test_rollover_atomic_closes_and_opens(paris_membership, paris_establishment):
    july = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=aware_local("Europe/Paris", 2026, 7, 20, 12),
        delta=35,
        idempotency_key="rollover-pts",
        source_id="r1",
    )
    august = rollover_establishment_if_due(
        paris_establishment,
        now=aware_local("Europe/Paris", 2026, 8, 1, 0, 5),
    )
    july.refresh_from_db()
    assert july.status == GamificationSeason.Status.CLOSED
    assert august is not None
    assert august.status == GamificationSeason.Status.ACTIVE
    assert august.starts_at == aware_local("Europe/Paris", 2026, 8, 1)
    assert sum_points_for_membership_season(paris_membership, august) == 0
    assert BadgeAward.objects.filter(season=july, membership=paris_membership).exists()


def test_rollover_idempotent(paris_establishment):
    open_season(paris_establishment, month_start_local=date(2026, 8, 1))
    first = rollover_establishment_if_due(
        paris_establishment,
        now=aware_local("Europe/Paris", 2026, 8, 15, 12),
    )
    second = rollover_establishment_if_due(
        paris_establishment,
        now=aware_local("Europe/Paris", 2026, 8, 15, 12),
    )
    assert first.id == second.id
    assert GamificationSeason.objects.filter(establishment=paris_establishment).count() == 1


def test_month_boundary_uses_local_not_utc(paris_establishment, paris_membership):
    # 2026-08-01 00:30 Paris == 2026-07-31 22:30 UTC — must attribute to August.
    open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    occurred = aware_local("Europe/Paris", 2026, 8, 1, 0, 30)
    assert occurred.astimezone(dt_timezone.utc).month == 7
    tx = _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=occurred,
        idempotency_key="local-month",
        source_id="lm1",
    )
    assert tx.season.starts_at == aware_local("Europe/Paris", 2026, 8, 1)


def test_ensure_rejects_past_gap_when_later_season_exists(paris_establishment):
    open_season(paris_establishment, month_start_local=date(2026, 8, 1))
    with pytest.raises(GamificationValidationError) as exc_info:
        ensure_season_for_occurred_at(
            paris_establishment,
            aware_local("Europe/Paris", 2026, 6, 15, 12),
        )
    assert exc_info.value.code == "gamification_season_past_gap"


def test_award_idempotent_after_close_no_side_effects(
    paris_membership,
    paris_establishment,
    monkeypatch,
):
    season = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    occurred_at = aware_local("Europe/Paris", 2026, 7, 15, 12)
    first = _award(
        membership=paris_membership,
        establishment=paris_establishment,
        occurred_at=occurred_at,
        delta=2,
        idempotency_key="idem-after-close",
        source_id="subj-close",
    )
    close_season(season, closed_at=aware_local("Europe/Paris", 2026, 8, 1))

    def _ensure_should_not_run(*args, **kwargs):
        raise AssertionError("ensure_season_for_occurred_at must not run on idempotent retry")

    with monkeypatch.context() as m:
        m.setattr(
            "houston.gamification.services.ensure_season_for_occurred_at",
            _ensure_should_not_run,
        )
        second = _award(
            membership=paris_membership,
            establishment=paris_establishment,
            occurred_at=occurred_at,
            delta=2,
            idempotency_key="idem-after-close",
            source_id="subj-close",
        )
        assert second.id == first.id

        with pytest.raises(GamificationIdempotencyConflictError):
            _award(
                membership=paris_membership,
                establishment=paris_establishment,
                occurred_at=occurred_at,
                delta=9,
                idempotency_key="idem-after-close",
                source_id="subj-close",
            )

    with pytest.raises(GamificationSeasonClosedError):
        _award(
            membership=paris_membership,
            establishment=paris_establishment,
            occurred_at=occurred_at,
            idempotency_key="new-after-close",
            source_id="subj-new",
        )


def test_award_metadata_safe_strips_disallowed_keys(paris_membership, paris_establishment):
    open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    tx = award_points(
        membership=paris_membership,
        establishment=paris_establishment,
        delta=1,
        reason_code="test.award",
        source_type="test",
        source_id="meta-1",
        occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
        idempotency_key="meta-safe",
        metadata_safe={"raw_observation": "secret text", "nested": {"a": 1}},
    )
    assert tx.metadata_safe == {}


@pytest.mark.django_db(transaction=True)
def test_concurrent_identical_awards_one_ledger_row(paris_membership, paris_establishment):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections

    occurred_at = aware_local("Europe/Paris", 2026, 7, 15, 12)
    key = "concurrent-same-award"

    def run_award():
        close_old_connections()
        try:
            return _award(
                membership=paris_membership,
                establishment=paris_establishment,
                occurred_at=occurred_at,
                delta=2,
                idempotency_key=key,
                source_id="subj-concurrent",
                source_event_id="evt-1",
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run_award), pool.submit(run_award)]
        results = [f.result(timeout=15) for f in futures]

    assert results[0].id == results[1].id
    assert PointTransaction.objects.filter(idempotency_key=key).count() == 1
    assert (
        GamificationSeason.objects.filter(
            establishment=paris_establishment,
            status=GamificationSeason.Status.ACTIVE,
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_award_integrity_error_fallback_deterministic(
    paris_membership,
    paris_establishment,
):
    import threading
    from unittest.mock import patch

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL-only concurrency test")

    open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    occurred_at = aware_local("Europe/Paris", 2026, 7, 15, 12)
    key = "idem-integrity-fallback"
    award_kwargs = dict(
        membership=paris_membership,
        establishment=paris_establishment,
        delta=2,
        reason_code="test.award",
        source_type="test",
        source_id="subj-integrity",
        source_event_id="evt-1",
        occurred_at=occurred_at,
        idempotency_key=key,
    )

    loser_past_early = threading.Event()
    winner_committed = threading.Event()
    loser_result: list[PointTransaction] = []
    loser_errors: list[BaseException] = []
    loser_thread_box: dict[str, threading.Thread | None] = {"thread": None}

    real_ensure = ensure_season_for_occurred_at

    def ensure_router(establishment, occurred_at, **kwargs):
        if threading.current_thread() is loser_thread_box["thread"]:
            loser_past_early.set()
            assert winner_committed.wait(timeout=5)
            return real_ensure(establishment, occurred_at, **kwargs)
        return real_ensure(establishment, occurred_at, **kwargs)

    def loser_txn() -> None:
        close_old_connections()
        try:
            loser_result.append(award_points(**award_kwargs))
        except BaseException as exc:
            loser_errors.append(exc)
        finally:
            close_old_connections()

    thread = threading.Thread(target=loser_txn, name="gamification-idem-loser")
    loser_thread_box["thread"] = thread

    with patch(
        "houston.gamification.services.ensure_season_for_occurred_at",
        ensure_router,
    ):
        thread.start()
        assert loser_past_early.wait(timeout=5)
        winner = award_points(**award_kwargs)
        winner_committed.set()
        thread.join(timeout=15)

    assert loser_errors == []
    assert len(loser_result) == 1
    assert loser_result[0].id == winner.id
    assert PointTransaction.objects.filter(idempotency_key=key).count() == 1
