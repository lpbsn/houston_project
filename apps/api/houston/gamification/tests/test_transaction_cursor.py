from __future__ import annotations

import uuid
from datetime import date

import pytest

from houston.gamification.constants import CURRENT_RULE_VERSION
from houston.gamification.models import PointTransaction
from houston.gamification.selectors import (
    build_point_transactions_page,
    point_transactions_queryset_for_membership,
)
from houston.gamification.services import open_season
from houston.gamification.tests.conftest import aware_local
from houston.gamification.transaction_cursor import (
    TransactionCursorError,
    decode_transaction_cursor,
    encode_transaction_cursor,
)

pytestmark = pytest.mark.django_db


def _create_transaction(
    *,
    membership,
    establishment,
    season,
    occurred_at,
    delta=1,
    transaction_id=None,
    idempotency_key=None,
):
    tx_id = transaction_id or uuid.uuid4()
    return PointTransaction.objects.create(
        id=tx_id,
        membership=membership,
        establishment=establishment,
        season=season,
        delta=delta,
        reason_code="test.award",
        source_type="test",
        source_id=str(tx_id),
        rule_version=CURRENT_RULE_VERSION,
        occurred_at=occurred_at,
        idempotency_key=idempotency_key or f"tx:{tx_id}",
    )


def test_transaction_cursor_is_url_safe():
    encoded = encode_transaction_cursor(
        occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
        transaction_id=uuid.uuid4(),
        season_id=uuid.uuid4(),
    )

    assert "+" not in encoded
    assert "/" not in encoded
    assert "=" not in encoded


def test_invalid_transaction_cursor_raises():
    with pytest.raises(TransactionCursorError):
        decode_transaction_cursor("not-valid", expected_season_id=None)


def test_transaction_cursor_rejects_season_filter_mismatch():
    cursor = encode_transaction_cursor(
        occurred_at=aware_local("Europe/Paris", 2026, 7, 15, 12),
        transaction_id=uuid.uuid4(),
        season_id=uuid.uuid4(),
    )

    with pytest.raises(TransactionCursorError):
        decode_transaction_cursor(cursor, expected_season_id=None)


def test_transaction_pagination_is_stable_when_occurred_at_matches(
    paris_membership,
    paris_establishment,
):
    season = open_season(paris_establishment, month_start_local=date(2026, 7, 1))
    occurred_at = aware_local("Europe/Paris", 2026, 7, 15, 12)
    for suffix in ("0001", "0002", "0003"):
        tx_id = uuid.UUID(f"00000000-0000-0000-0000-00000000{suffix}")
        _create_transaction(
            membership=paris_membership,
            establishment=paris_establishment,
            season=season,
            occurred_at=occurred_at,
            transaction_id=tx_id,
        )
    ordered = list(
        point_transactions_queryset_for_membership(
            membership=paris_membership,
            establishment_id=paris_establishment.id,
        )
    )

    page_one = build_point_transactions_page(
        membership=paris_membership,
        establishment_id=paris_establishment.id,
        season_id=None,
        cursor=None,
        page_size=2,
    )
    page_two = build_point_transactions_page(
        membership=paris_membership,
        establishment_id=paris_establishment.id,
        season_id=None,
        cursor=page_one.next_cursor,
        page_size=2,
    )

    assert page_one.has_more is True
    assert page_one.next_cursor is not None
    assert [item.id for item in page_one.items] == [item.id for item in ordered[:2]]
    assert [item.id for item in page_two.items] == [ordered[2].id]
    assert {item.id for item in page_one.items + page_two.items} == {
        item.id for item in ordered
    }
