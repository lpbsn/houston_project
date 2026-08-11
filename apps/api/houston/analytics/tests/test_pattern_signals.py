from __future__ import annotations

import base64
import json
from datetime import timedelta

import pytest
from django.utils import timezone

from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.pattern_signals import (
    MAX_PATTERN_SIGNALS_PAGE_SIZE,
    PATTERN_SIGNALS_CURSOR_VERSION,
    list_analytics_pattern_signals,
)
from houston.analytics.services import create_operational_pattern
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.factories import build_membership, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def create_signal(
    membership,
    *,
    title="Signal",
    status=Signal.Status.OPEN,
    routing_status=Signal.RoutingStatus.RESOLVED,
    created_at=None,
    resolved_at=None,
    merged_into=None,
    affected_business_unit=None,
    responsible_business_unit=None,
):
    signal = Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        routing_status=routing_status,
        status=status,
        title=title,
        structured_summary=f"Summary for {title}.",
        issue_focus=title.lower().replace(" ", "-"),
        merged_into=merged_into,
        last_activity_at=created_at or timezone.now(),
        resolved_at=resolved_at,
    )
    if created_at is not None:
        Signal.objects.filter(pk=signal.pk).update(created_at=created_at)
        signal.refresh_from_db()
    return signal


def create_pattern(membership, *, label="Pattern"):
    return create_operational_pattern(
        organization=membership.establishment.organization,
        label=label,
        created_by_membership=membership,
    )


def assign_signal(signal, pattern):
    return SignalPatternAssignment.objects.create(
        signal=signal,
        pattern=pattern,
        classification_status=SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
        assigned_signature=f"sig-{signal.id}",
        assigned_classifier_version="classifier-v1",
        assigned_at=timezone.now(),
    )


def add_signal(membership, pattern, *, title, created_at, **kwargs):
    signal = create_signal(
        membership,
        title=title,
        created_at=created_at,
        **kwargs,
    )
    assign_signal(signal, pattern)
    return signal


def test_pattern_signals_lists_visible_items_in_created_at_desc_order():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Water leak")
    start = timezone.now()
    end = start + timedelta(days=1)
    first = add_signal(owner, pattern, title="First", created_at=start)
    latest = add_signal(
        owner,
        pattern,
        title="Latest",
        created_at=start + timedelta(hours=2),
        resolved_at=start + timedelta(hours=3),
    )
    add_signal(owner, pattern, title="End excluded", created_at=end)

    result = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert [item.signal_id for item in result.items] == [latest.id, first.id]
    assert result.items[0].title == "Latest"
    assert result.items[0].structured_summary == "Summary for Latest."
    assert result.items[0].status == Signal.Status.OPEN
    assert result.items[0].resolved_at == start + timedelta(hours=3)
    assert result.items[0].establishment.id == owner.establishment_id
    assert result.items[0].establishment.name == owner.establishment.name
    assert result.page_size == 50
    assert not result.has_more
    assert result.next_cursor is None
    assert not hasattr(result, "total_count")


@pytest.mark.parametrize("pattern_id_value", ["missing", "other_tenant", "previous_only"])
def test_pattern_signals_masks_missing_cross_tenant_and_without_period_occurrence(
    pattern_id_value,
):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    other_owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Visible")
    other_pattern = create_pattern(other_owner, label="Other tenant")
    start = timezone.now()
    end = start + timedelta(days=1)
    add_signal(owner, pattern, title="Previous", created_at=start - timedelta(hours=1))
    add_signal(other_owner, other_pattern, title="Hidden", created_at=start)

    pattern_id = {
        "missing": "not-a-uuid",
        "other_tenant": other_pattern.id,
        "previous_only": pattern.id,
    }[pattern_id_value]

    with pytest.raises(AnalyticsValidationError) as exc_info:
        list_analytics_pattern_signals(
            owner.user,
            pattern_id=pattern_id,
            period_start=start,
            period_end=end,
        )

    assert exc_info.value.code == "analytics_pattern_not_found"


def test_pattern_signals_returns_empty_page_when_cursor_outlives_visible_dataset():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Cursor mutation")
    start = timezone.now()
    end = start + timedelta(days=1)
    first_signal = add_signal(
        owner,
        pattern,
        title="First page",
        created_at=start + timedelta(hours=2),
    )
    second_signal = add_signal(
        owner,
        pattern,
        title="Second page",
        created_at=start + timedelta(hours=1),
    )
    first = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
        page_size=1,
    )
    assert first.items[0].signal_id == first_signal.id
    assert first.has_more

    Signal.objects.filter(pk=second_signal.pk).update(status=Signal.Status.CANCELED)
    second = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
        page_size=1,
        cursor=first.next_cursor,
    )

    assert second.items == ()
    assert not second.has_more
    assert second.next_cursor is None


def test_pattern_signals_respects_manager_business_unit_and_unassigned_scope():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    pattern = create_pattern(manager, label="Manager visible")
    in_scope_bu = create_business_unit(establishment=manager.establishment, key="bar")
    out_scope_bu = create_business_unit(
        establishment=manager.establishment,
        key="kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=in_scope_bu,
    )
    start = timezone.now()
    end = start + timedelta(days=1)
    scoped = add_signal(
        manager,
        pattern,
        title="BU scoped",
        created_at=start + timedelta(minutes=1),
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    unassigned = add_signal(
        manager,
        pattern,
        title="Unassigned",
        created_at=start + timedelta(minutes=2),
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )
    add_signal(
        manager,
        pattern,
        title="Out of scope",
        created_at=start + timedelta(minutes=3),
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )

    result = list_analytics_pattern_signals(
        manager.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert [item.signal_id for item in result.items] == [unassigned.id, scoped.id]


def test_pattern_signals_staff_cannot_use_existing_pattern_id():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    staff = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    pattern = create_pattern(owner, label="Hidden from staff")
    start = timezone.now()
    end = start + timedelta(days=1)
    add_signal(owner, pattern, title="Visible to owner", created_at=start)

    with pytest.raises(AnalyticsValidationError) as exc_info:
        list_analytics_pattern_signals(
            staff.user,
            pattern_id=pattern.id,
            period_start=start,
            period_end=end,
        )

    assert exc_info.value.code == "analytics_pattern_not_found"


def test_pattern_signals_uses_status_matrix():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Status matrix")
    start = timezone.now()
    end = start + timedelta(days=1)
    survivor = create_signal(owner, title="Survivor", created_at=start)
    included = [
        add_signal(owner, pattern, title="Open", created_at=start),
        add_signal(
            owner,
            pattern,
            title="Interesting",
            status=Signal.Status.INTERESTING,
            created_at=start + timedelta(minutes=1),
        ),
        add_signal(
            owner,
            pattern,
            title="Resolved",
            status=Signal.Status.RESOLVED,
            created_at=start + timedelta(minutes=2),
        ),
        add_signal(
            owner,
            pattern,
            title="Archived",
            status=Signal.Status.ARCHIVED,
            created_at=start + timedelta(minutes=3),
        ),
    ]
    add_signal(
        owner,
        pattern,
        title="Canceled",
        status=Signal.Status.CANCELED,
        created_at=start + timedelta(minutes=4),
    )
    add_signal(
        owner,
        pattern,
        title="Merged",
        created_at=start + timedelta(minutes=5),
        merged_into=survivor,
    )

    result = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert {item.signal_id for item in result.items} == {signal.id for signal in included}


def test_pattern_signals_paginates_without_duplicates_on_unchanged_dataset():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Pagination")
    start = timezone.now()
    end = start + timedelta(days=1)
    signals = [
        add_signal(owner, pattern, title=f"Signal {index}", created_at=start)
        for index in range(3)
    ]

    first = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
        page_size=2,
    )
    second = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
        page_size=2,
        cursor=first.next_cursor,
    )

    served_ids = [item.signal_id for item in first.items + second.items]
    expected_ids = [
        signal.id
        for signal in sorted(
            signals,
            key=lambda signal: (signal.created_at, signal.id),
            reverse=True,
        )
    ]
    assert first.has_more
    assert not second.has_more
    assert served_ids == expected_ids
    assert len(served_ids) == len(set(served_ids)) == 3


@pytest.mark.parametrize(
    "change",
    ["user", "pattern", "period", "organization", "establishment", "page_size"],
)
def test_pattern_signals_cursor_rejects_incompatible_context(change):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    other_user = build_membership(role=EstablishmentMembership.Role.OWNER).user
    other_establishment = Establishment.objects.create(
        name="Other scoped",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    create_membership(
        establishment=other_establishment,
        user=owner.user,
        role=EstablishmentMembership.Role.OWNER,
    )
    pattern = create_pattern(owner, label="Cursor")
    other_pattern = create_pattern(owner, label="Other cursor")
    start = timezone.now()
    end = start + timedelta(days=1)
    add_signal(owner, pattern, title="One", created_at=start + timedelta(minutes=2))
    add_signal(owner, pattern, title="Two", created_at=start + timedelta(minutes=1))
    first = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
        organization_id=owner.establishment.organization_id,
        page_size=1,
    )
    kwargs = {
        "user": owner.user,
        "pattern_id": pattern.id,
        "period_start": start,
        "period_end": end,
        "organization_id": owner.establishment.organization_id,
        "establishment_id": None,
        "page_size": 1,
        "cursor": first.next_cursor,
    }
    if change == "user":
        kwargs["user"] = other_user
    elif change == "pattern":
        kwargs["pattern_id"] = other_pattern.id
    elif change == "period":
        kwargs["period_end"] = end + timedelta(hours=1)
    elif change == "organization":
        kwargs["organization_id"] = None
    elif change == "establishment":
        kwargs["establishment_id"] = other_establishment.id
    elif change == "page_size":
        kwargs["page_size"] = 2

    with pytest.raises(AnalyticsValidationError) as exc_info:
        list_analytics_pattern_signals(**kwargs)

    assert exc_info.value.code == "analytics_pattern_signals_cursor_invalid"


def test_pattern_signals_cursor_rejects_invalid_incomplete_or_unknown_version():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Cursor invalid")
    start = timezone.now()
    end = start + timedelta(days=1)

    with pytest.raises(AnalyticsValidationError) as exc_info:
        list_analytics_pattern_signals(
            owner.user,
            pattern_id=pattern.id,
            period_start=start,
            period_end=end,
            cursor="not-a-cursor",
        )
    assert exc_info.value.code == "analytics_pattern_signals_cursor_invalid"

    for payload in (
        {"version": "analytics_pattern_signals_v0", "context": {}, "sort": {}},
        {"version": PATTERN_SIGNALS_CURSOR_VERSION, "context": {}},
    ):
        raw = json.dumps(payload).encode()
        cursor = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        with pytest.raises(AnalyticsValidationError) as exc_info:
            list_analytics_pattern_signals(
                owner.user,
                pattern_id=pattern.id,
                period_start=start,
                period_end=end,
                cursor=cursor,
            )
        assert exc_info.value.code == "analytics_pattern_signals_cursor_invalid"


@pytest.mark.parametrize("page_size", [0, MAX_PATTERN_SIGNALS_PAGE_SIZE + 1])
def test_pattern_signals_rejects_invalid_page_size(page_size):
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Page size")
    start = timezone.now()
    end = start + timedelta(days=1)

    with pytest.raises(AnalyticsValidationError) as exc_info:
        list_analytics_pattern_signals(
            owner.user,
            pattern_id=pattern.id,
            period_start=start,
            period_end=end,
            page_size=page_size,
        )

    assert exc_info.value.code == "analytics_pattern_signals_page_size_invalid"


def test_pattern_signals_payload_exposes_only_safe_business_unit_ref():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    hidden_membership = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Safe payload")
    visible_bu = create_business_unit(
        establishment=owner.establishment,
        key="front_desk",
        label="Front Desk",
    )
    hidden_bu = create_business_unit(
        establishment=hidden_membership.establishment,
        key="kitchen",
        label="Kitchen",
    )
    start = timezone.now()
    end = start + timedelta(days=1)
    visible = add_signal(
        owner,
        pattern,
        title="Visible",
        created_at=start,
        responsible_business_unit=visible_bu,
    )
    add_signal(
        hidden_membership,
        pattern,
        title="Hidden",
        created_at=start + timedelta(minutes=1),
        responsible_business_unit=hidden_bu,
    )

    result = list_analytics_pattern_signals(
        owner.user,
        pattern_id=pattern.id,
        period_start=start,
        period_end=end,
    )

    assert [item.signal_id for item in result.items] == [visible.id]
    item = result.items[0]
    assert item.responsible_business_unit is not None
    assert item.responsible_business_unit.id == visible_bu.id
    assert item.responsible_business_unit.specific_name == "Front Desk"
    assert not hasattr(item, "assignment_source")
    assert not hasattr(item, "routing_key")
    assert not hasattr(item, "location_text")
    assert not hasattr(item, "issue_focus")
    assert not hasattr(item.responsible_business_unit, "routing_key")
