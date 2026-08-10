from __future__ import annotations

import base64
import json
from datetime import timedelta

import pytest
from django.utils import timezone

from houston.analytics.comparisons import (
    RELATIVE_CHANGE_COMPUTED,
    RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO,
)
from houston.analytics.exceptions import AnalyticsValidationError
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.pattern_list import (
    MAX_PATTERN_LIST_ESTABLISHMENTS,
    PATTERN_LIST_CURSOR_VERSION,
    list_analytics_patterns,
)
from houston.analytics.recurrence import RECURRENCE_STATUS_COMPUTED
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
        structured_summary="Structured signal summary.",
        issue_focus=title.lower().replace(" ", "-"),
        merged_into=merged_into,
        last_activity_at=created_at or timezone.now(),
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


def test_pattern_list_counts_current_previous_and_boundaries_without_previous_only_rows():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Water leak")
    previous_only = create_pattern(owner, label="Previous only")
    period_start = timezone.now()
    period_end = period_start + timedelta(days=7)
    previous_start = period_start - timedelta(days=7)

    add_signal(owner, pattern, title="Previous", created_at=previous_start)
    add_signal(owner, pattern, title="Current start", created_at=period_start)
    add_signal(
        owner,
        pattern,
        title="Current latest",
        created_at=period_start + timedelta(days=1),
    )
    add_signal(owner, pattern, title="Current end", created_at=period_end)
    add_signal(owner, previous_only, title="Only previous", created_at=previous_start)

    result = list_analytics_patterns(
        owner.user,
        period_start=period_start,
        period_end=period_end,
    )

    assert [item.pattern_id for item in result.items] == [pattern.id]
    item = result.items[0]
    assert item.signal_count == 2
    assert item.previous_signal_count == 1
    assert item.signal_count_comparison.absolute_delta == 1
    assert item.signal_count_comparison.relative_change == 1
    assert item.signal_count_comparison.relative_change_status == RELATIVE_CHANGE_COMPUTED
    assert item.last_seen_at == period_start + timedelta(days=1)
    assert result.previous_period.period_start == previous_start
    assert result.previous_period.period_end == period_start


def test_pattern_list_reports_previous_zero_relative_change_as_undefined():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="No previous")
    start = timezone.now()
    end = start + timedelta(days=7)
    add_signal(owner, pattern, title="Current", created_at=start + timedelta(hours=1))

    item = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    ).items[0]

    assert item.previous_signal_count == 0
    assert item.signal_count_comparison.absolute_delta == 1
    assert item.signal_count_comparison.relative_change is None
    assert (
        item.signal_count_comparison.relative_change_status
        == RELATIVE_CHANGE_UNDEFINED_PREVIOUS_ZERO
    )


def test_actionable_and_status_matrix_filters_are_reused():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Status mix")
    start = timezone.now()
    end = start + timedelta(days=1)
    survivor = create_signal(owner, title="Survivor", created_at=start)

    add_signal(owner, pattern, title="Open", created_at=start + timedelta(minutes=1))
    add_signal(
        owner,
        pattern,
        title="Interesting",
        status=Signal.Status.INTERESTING,
        created_at=start + timedelta(minutes=2),
    )
    add_signal(
        owner,
        pattern,
        title="Canceled",
        status=Signal.Status.CANCELED,
        created_at=start + timedelta(minutes=3),
    )
    add_signal(
        owner,
        pattern,
        title="Merged",
        created_at=start + timedelta(minutes=4),
        merged_into=survivor,
    )

    item = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    ).items[0]

    assert item.signal_count == 2
    assert item.actionable_signal_count == 1


def test_pattern_list_respects_scope_and_manager_business_unit_unassigned_visibility():
    manager = build_membership(role=EstablishmentMembership.Role.MANAGER)
    pattern = create_pattern(manager, label="Manager visible")
    hidden_pattern = create_pattern(manager, label="Manager hidden")
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

    add_signal(
        manager,
        pattern,
        title="BU scoped",
        created_at=start + timedelta(minutes=1),
        affected_business_unit=in_scope_bu,
        responsible_business_unit=in_scope_bu,
    )
    add_signal(
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
        hidden_pattern,
        title="Out of scope",
        created_at=start + timedelta(minutes=3),
        affected_business_unit=out_scope_bu,
        responsible_business_unit=out_scope_bu,
    )

    result = list_analytics_patterns(
        manager.user,
        period_start=start,
        period_end=end,
    )

    assert [item.pattern_id for item in result.items] == [pattern.id]
    assert result.items[0].signal_count == 2


def test_pattern_list_does_not_leak_hidden_signals_or_establishments():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    hidden_establishment = Establishment.objects.create(
        name="Hidden",
        organization=owner.establishment.organization,
        status=Establishment.Status.ACTIVE,
        timezone="UTC",
    )
    hidden_membership = create_membership(
        establishment=hidden_establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    shared_pattern = create_pattern(owner, label="Shared")
    hidden_pattern = create_pattern(owner, label="Hidden")
    start = timezone.now()
    end = start + timedelta(days=1)

    add_signal(owner, shared_pattern, title="Visible", created_at=start)
    add_signal(
        hidden_membership,
        shared_pattern,
        title="Hidden shared",
        created_at=start,
    )
    add_signal(
        hidden_membership,
        hidden_pattern,
        title="Hidden only",
        created_at=start,
    )

    result = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    )

    assert [item.pattern_id for item in result.items] == [shared_pattern.id]
    item = result.items[0]
    assert item.signal_count == 1
    assert item.establishment_count == 1
    assert [summary.name for summary in item.establishments] == [
        owner.establishment.name,
    ]


def test_establishment_summaries_are_bounded_ordered_with_exact_total_count():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Multi site")
    start = timezone.now()
    end = start + timedelta(days=1)
    memberships = [owner]
    for index in range(MAX_PATTERN_LIST_ESTABLISHMENTS + 2):
        establishment = Establishment.objects.create(
            name=f"Site {index}",
            organization=owner.establishment.organization,
            status=Establishment.Status.ACTIVE,
            timezone="UTC",
        )
        memberships.append(
            create_membership(
                establishment=establishment,
                user=owner.user,
                role=EstablishmentMembership.Role.OWNER,
            )
        )
    for index, membership in enumerate(memberships):
        add_signal(
            membership,
            pattern,
            title=f"Signal {index}",
            created_at=start + timedelta(minutes=index),
        )
    add_signal(
        memberships[1],
        pattern,
        title="Extra for first site",
        created_at=start + timedelta(hours=1),
    )

    item = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    ).items[0]

    assert item.establishment_count == len(memberships)
    assert len(item.establishments) == MAX_PATTERN_LIST_ESTABLISHMENTS
    assert item.establishments[0].name == memberships[1].establishment.name
    assert item.establishments[0].signal_count == 2


def test_pattern_list_paginates_deterministically_without_duplicates_on_unchanged_data():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)
    patterns = [
        create_pattern(owner, label="Alpha"),
        create_pattern(owner, label="Beta"),
        create_pattern(owner, label="Gamma"),
    ]
    add_signal(owner, patterns[0], title="Alpha one", created_at=start)
    add_signal(owner, patterns[0], title="Alpha two", created_at=start + timedelta(hours=1))
    add_signal(owner, patterns[1], title="Beta", created_at=start + timedelta(hours=2))
    add_signal(owner, patterns[2], title="Gamma", created_at=start + timedelta(hours=3))

    first = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
        page_size=2,
    )
    second = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
        page_size=2,
        cursor=first.next_cursor,
    )

    served_ids = [item.pattern_id for item in first.items + second.items]
    assert first.has_more
    assert not second.has_more
    assert len(served_ids) == len(set(served_ids)) == 3
    assert served_ids == [patterns[0].id, patterns[2].id, patterns[1].id]


@pytest.mark.parametrize(
    "change",
    ["user", "period", "organization", "establishment", "page_size"],
)
def test_pattern_list_cursor_rejects_incompatible_context(change):
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
    second_pattern = create_pattern(owner, label="Cursor next")
    start = timezone.now()
    end = start + timedelta(days=1)
    add_signal(owner, pattern, title="Cursor one", created_at=start + timedelta(hours=1))
    add_signal(owner, second_pattern, title="Cursor two", created_at=start)
    first = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
        organization_id=owner.establishment.organization_id,
        page_size=1,
    )
    kwargs = {
        "user": owner.user,
        "period_start": start,
        "period_end": end,
        "organization_id": owner.establishment.organization_id,
        "establishment_id": None,
        "page_size": 1,
        "cursor": first.next_cursor,
    }
    if change == "user":
        kwargs["user"] = other_user
    elif change == "period":
        kwargs["period_end"] = end + timedelta(hours=1)
    elif change == "organization":
        kwargs["organization_id"] = None
    elif change == "establishment":
        kwargs["establishment_id"] = other_establishment.id
    elif change == "page_size":
        kwargs["page_size"] = 2

    with pytest.raises(AnalyticsValidationError) as exc_info:
        list_analytics_patterns(**kwargs)

    assert exc_info.value.code == "analytics_pattern_list_cursor_invalid"


def test_pattern_list_cursor_rejects_invalid_or_unknown_version():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)

    with pytest.raises(AnalyticsValidationError):
        list_analytics_patterns(
            owner.user,
            period_start=start,
            period_end=end,
            cursor="not-a-cursor",
        )

    payload = {
        "version": "analytics_pattern_list_v0",
        "context": {},
        "sort": {},
    }
    raw = json.dumps(payload).encode()
    cursor = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    assert PATTERN_LIST_CURSOR_VERSION != payload["version"]

    with pytest.raises(AnalyticsValidationError):
        list_analytics_patterns(
            owner.user,
            period_start=start,
            period_end=end,
            cursor=cursor,
        )


def test_pattern_list_recalculates_after_dataset_change_between_pages():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)
    first_pattern = create_pattern(owner, label="Alpha")
    second_pattern = create_pattern(owner, label="Beta")
    add_signal(owner, first_pattern, title="Alpha", created_at=start)
    add_signal(owner, second_pattern, title="Beta", created_at=start + timedelta(hours=1))

    first = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
        page_size=1,
    )
    new_middle_pattern = create_pattern(owner, label="Zulu")
    add_signal(
        owner,
        new_middle_pattern,
        title="Zulu",
        created_at=start + timedelta(minutes=30),
    )

    second = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
        page_size=1,
        cursor=first.next_cursor,
    )

    assert first.items[0].pattern_id == second_pattern.id
    assert second.items[0].pattern_id == new_middle_pattern.id


def test_pattern_list_recalculates_historical_periods_from_current_assignment_state():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Historical")
    start = timezone.now()
    end = start + timedelta(days=1)
    signal = create_signal(
        owner,
        title="Historical signal",
        created_at=start + timedelta(hours=1),
    )

    before = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    )
    assign_signal(signal, pattern)
    after = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    )

    assert before.items == ()
    assert [item.pattern_id for item in after.items] == [pattern.id]


def test_pattern_list_validates_page_size_and_reports_computed_recurrence():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)

    with pytest.raises(AnalyticsValidationError) as low:
        list_analytics_patterns(owner.user, period_start=start, period_end=end, page_size=0)
    assert low.value.code == "analytics_pattern_list_page_size_invalid"

    result = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    )

    assert result.recurrence_status == RECURRENCE_STATUS_COMPUTED


def test_pattern_list_sorts_recurrent_patterns_first_before_pagination():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    recurring = create_pattern(owner, label="Recurring")
    frequent = create_pattern(owner, label="Frequent non recurrent")
    start = timezone.now()
    end = start + timedelta(days=7)

    for index, created_at in enumerate(
        [
            end - timedelta(days=20),
            end - timedelta(days=19),
            start + timedelta(hours=1),
        ]
    ):
        add_signal(owner, recurring, title=f"Recurring {index}", created_at=created_at)
    for index in range(4):
        add_signal(
            owner,
            frequent,
            title=f"Frequent {index}",
            created_at=start + timedelta(minutes=index),
        )

    result = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
        page_size=1,
    )

    assert result.items[0].pattern_id == recurring.id
    assert result.items[0].is_recurrent is True
    assert result.items[0].occurrence_count_30d == 3
    assert result.has_more


def test_pattern_list_zero_fills_visible_pattern_without_recent_recurrence_occurrences():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Old visible")
    end = timezone.now()
    start = end - timedelta(days=90)
    add_signal(
        owner,
        pattern,
        title="Old occurrence",
        created_at=end - timedelta(days=60),
    )

    item = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    ).items[0]

    assert item.pattern_id == pattern.id
    assert item.signal_count == 1
    assert item.is_recurrent is False
    assert item.occurrence_count_30d == 0
    assert item.distinct_day_count_30d == 0


def test_pattern_list_excludes_recurrent_pattern_absent_from_current_ui_period():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    pattern = create_pattern(owner, label="Recent but outside UI")
    end = timezone.now()
    start = end - timedelta(days=7)
    for index, created_at in enumerate(
        [
            end - timedelta(days=20),
            end - timedelta(days=19),
            end - timedelta(days=8),
        ]
    ):
        add_signal(owner, pattern, title=f"Outside {index}", created_at=created_at)

    result = list_analytics_patterns(
        owner.user,
        period_start=start,
        period_end=end,
    )

    assert result.items == ()


def test_pattern_list_cursor_rejects_v1_after_recurrence_sort_change():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    start = timezone.now()
    end = start + timedelta(days=1)
    payload = {
        "version": "analytics_pattern_list_v1",
        "context": {
            "user_id": str(owner.user_id),
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "organization_id": None,
            "establishment_id": None,
            "page_size": 50,
        },
        "sort": {},
    }
    cursor = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")

    with pytest.raises(AnalyticsValidationError) as exc_info:
        list_analytics_patterns(
            owner.user,
            period_start=start,
            period_end=end,
            cursor=cursor,
        )

    assert exc_info.value.code == "analytics_pattern_list_cursor_invalid"
