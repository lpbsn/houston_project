from __future__ import annotations

import uuid
from datetime import date

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import UserSession
from houston.establishments.models import EstablishmentMembership
from houston.gamification.constants import (
    CURRENT_RULE_VERSION,
    REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
    REASON_EXECUTION_REVIEWED,
    REASON_RECURRING_EXECUTION_DONE,
    REASON_RESOLUTION_REQUEST_APPROVED,
    REASON_SIGNAL_MARKED_INTERESTING,
    REASON_SIGNAL_MOVED_IN_PROGRESS,
    REASON_SIGNAL_RESOLVED,
    SOURCE_TYPE_ACTION_PLAN_EXECUTION,
)
from houston.gamification.models import GamificationSeason, PointTransaction
from houston.gamification.selectors import point_transactions_queryset_for_membership
from houston.gamification.services import award_points, open_season
from houston.gamification.tests.conftest import aware_local
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_establishment, create_membership, create_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def overview_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/gamification/me/"


def transactions_url(establishment_id, query: str = "") -> str:
    return f"/api/v1/establishments/{establishment_id}/gamification/me/transactions/{query}"


def _award(
    *,
    membership,
    establishment,
    occurred_at,
    delta,
    reason_code="test.award",
    source_type="test",
    source_id=None,
    metadata_safe=None,
    idempotency_key=None,
):
    sid = source_id or str(uuid.uuid4())
    return award_points(
        membership=membership,
        establishment=establishment,
        delta=delta,
        reason_code=reason_code,
        source_type=source_type,
        source_id=sid,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key or f"{reason_code}:{sid}:{membership.id}",
        metadata_safe=metadata_safe,
    )


def _create_transaction(
    *,
    membership,
    establishment,
    season,
    occurred_at,
    transaction_id=None,
    source_type="test",
    source_id=None,
):
    tx_id = transaction_id or uuid.uuid4()
    return PointTransaction.objects.create(
        id=tx_id,
        membership=membership,
        establishment=establishment,
        season=season,
        delta=1,
        reason_code="test.award",
        source_type=source_type,
        source_id=source_id or str(tx_id),
        rule_version=CURRENT_RULE_VERSION,
        occurred_at=occurred_at,
        idempotency_key=f"tx:{tx_id}",
        metadata_safe={"raw_observation": "secret"},
    )


def test_overview_requires_authentication(api_client):
    membership = build_api_membership()

    response = api_client.get(overview_url(membership.establishment_id))

    assert response.status_code == 401


def test_overview_uses_existing_establishment_scope_resolution(api_client):
    user = create_user(username="multi-establishment")
    selected_establishment = create_establishment(name="Selected", timezone="UTC")
    path_establishment = create_establishment(name="Path", timezone="UTC")
    create_membership(establishment=selected_establishment, user=user)
    path_membership = create_membership(establishment=path_establishment, user=user)
    token = login(api_client, user=user)
    session = UserSession.objects.get(user=user)
    session.selected_establishment = selected_establishment
    session.save(update_fields=["selected_establishment", "updated_at"])

    response = api_client.get(
        overview_url(path_membership.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_inactive_membership_is_refused(api_client):
    membership = build_api_membership(
        membership_status=EstablishmentMembership.Status.DEACTIVATED,
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        overview_url(membership.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 403


def test_overview_without_current_season_does_not_mutate(api_client, monkeypatch):
    membership = build_api_membership()
    monkeypatch.setattr(
        "houston.gamification.selectors.timezone.now",
        lambda: aware_local("UTC", 2026, 7, 20, 12),
    )
    before = GamificationSeason.objects.count()
    token = login(api_client, user=membership.user)

    response = api_client.get(
        overview_url(membership.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current"]["season_id"] is None
    assert body["current"]["score"] == 0
    assert body["current"]["next_grade"] == "bronze"
    assert GamificationSeason.objects.count() == before


def test_overview_returns_score_progress_and_rules(api_client):
    membership = build_api_membership()
    establishment = membership.establishment
    open_season(establishment, month_start_local=date(2026, 7, 1))
    _award(
        membership=membership,
        establishment=establishment,
        occurred_at=aware_local("UTC", 2026, 7, 5, 12),
        delta=47,
        reason_code=REASON_SIGNAL_MARKED_INTERESTING,
        idempotency_key="overview-score",
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        overview_url(establishment.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current"]["score"] == 47
    assert body["current"]["grade"] == "bronze"
    assert body["current"]["next_grade"] == "silver"
    assert body["current"]["points_to_next_grade"] == 3
    assert body["current"]["progress_ratio"] == 0.94
    rule_codes = {rule["code"] for rule in body["rules"]["points"]}
    assert {
        REASON_SIGNAL_MARKED_INTERESTING,
        REASON_SIGNAL_MOVED_IN_PROGRESS,
        REASON_SIGNAL_RESOLVED,
        REASON_RESOLUTION_REQUEST_APPROVED,
        REASON_ACTION_PLAN_EXECUTION_STARTED_ELIGIBLE,
        REASON_RECURRING_EXECUTION_DONE,
        REASON_EXECUTION_REVIEWED,
        "signal.canceled",
    } <= rule_codes


def test_transactions_payload_is_allowlisted(api_client):
    membership = build_api_membership()
    establishment = membership.establishment
    season = open_season(establishment, month_start_local=date(2026, 7, 1))
    safe_source_id = uuid.uuid4()
    _create_transaction(
        membership=membership,
        establishment=establishment,
        season=season,
        occurred_at=aware_local("UTC", 2026, 7, 5, 12),
        source_type=SOURCE_TYPE_ACTION_PLAN_EXECUTION,
        source_id=str(safe_source_id),
    )
    unsafe = _create_transaction(
        membership=membership,
        establishment=establishment,
        season=season,
        occurred_at=aware_local("UTC", 2026, 7, 6, 12),
        source_type="observation_raw_text",
        source_id="private-source",
    )
    token = login(api_client, user=membership.user)

    response = api_client.get(
        transactions_url(establishment.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    items = response.json()["items"]
    unsafe_item = next(item for item in items if item["id"] == str(unsafe.id))
    safe_item = next(item for item in items if item["source"] is not None)
    assert unsafe_item["source"] is None
    assert "metadata_safe" not in unsafe_item
    assert safe_item["source"] == {
        "type": SOURCE_TYPE_ACTION_PLAN_EXECUTION,
        "id": str(safe_source_id),
    }


def test_transactions_cursor_pagination_has_no_duplicates_or_omissions(api_client):
    membership = build_api_membership()
    establishment = membership.establishment
    season = open_season(establishment, month_start_local=date(2026, 7, 1))
    occurred_at = aware_local("UTC", 2026, 7, 15, 12)
    for suffix in ("0001", "0002", "0003"):
        tx_id = uuid.UUID(f"00000000-0000-0000-0000-00000000{suffix}")
        _create_transaction(
            membership=membership,
            establishment=establishment,
            season=season,
            occurred_at=occurred_at,
            transaction_id=tx_id,
        )
    ordered = list(
        point_transactions_queryset_for_membership(
            membership=membership,
            establishment_id=establishment.id,
        )
    )
    token = login(api_client, user=membership.user)

    first = api_client.get(
        transactions_url(establishment.id, "?page_size=2"),
        **auth_headers(token),
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["has_more"] is True
    assert first_body["next_cursor"] is not None
    assert [item["id"] for item in first_body["items"]] == [
        str(item.id) for item in ordered[:2]
    ]

    second = api_client.get(
        transactions_url(establishment.id, f"?page_size=2&cursor={first_body['next_cursor']}"),
        **auth_headers(token),
    )
    assert second.status_code == 200
    ids = [item["id"] for item in first_body["items"] + second.json()["items"]]
    assert ids == [str(item.id) for item in ordered]
    assert len(ids) == len(set(ids))


def test_transaction_cursor_season_mismatch_returns_400(api_client):
    membership = build_api_membership()
    establishment = membership.establishment
    july = open_season(establishment, month_start_local=date(2026, 7, 1))
    _create_transaction(
        membership=membership,
        establishment=establishment,
        season=july,
        occurred_at=aware_local("UTC", 2026, 7, 15, 12),
    )
    _create_transaction(
        membership=membership,
        establishment=establishment,
        season=july,
        occurred_at=aware_local("UTC", 2026, 7, 16, 12),
    )
    other_season_id = uuid.uuid4()
    token = login(api_client, user=membership.user)

    first = api_client.get(
        transactions_url(establishment.id, f"?season_id={july.id}&page_size=1"),
        **auth_headers(token),
    )
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor is not None

    mismatched = api_client.get(
        transactions_url(establishment.id, f"?season_id={other_season_id}&cursor={cursor}"),
        **auth_headers(token),
    )

    assert mismatched.status_code == 400
    assert mismatched.json()["code"] == "validation_error"
