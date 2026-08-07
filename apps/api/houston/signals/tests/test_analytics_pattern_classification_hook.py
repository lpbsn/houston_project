from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.observations.models import Observation
from houston.signals.models import Signal
from houston.signals.services import (
    ResolvedTaxonomy,
    aggregate_candidate_into_signal,
    create_signal_from_candidate,
    normalize_issue_focus,
    qualify_signal_routing,
)
from houston.signals.tests.pipeline_helpers import mojito_candidate
from houston.testing.factories import build_membership

pytestmark = pytest.mark.django_db(transaction=True)


def setup_signal_context(*, role=EstablishmentMembership.Role.STAFF):
    membership = build_membership(role=role)
    bar = create_business_unit(
        establishment=membership.establishment,
        key="bar",
        label="Bar",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=bar,
        label="Stock",
    )
    observation = Observation.objects.create(
        establishment=membership.establishment,
        submitted_by_membership=membership,
        raw_text="Le sirop mojito est vide.",
        submitted_at=timezone.now(),
    )
    return membership, bar, subject, observation


def create_resolved_signal(membership, bar, subject, *, title="Issue", issue_focus="stock"):
    return Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary="Structured issue summary",
        issue_focus=normalize_issue_focus(issue_focus),
        last_activity_at=timezone.now(),
    )


def test_create_signal_from_candidate_schedules_analytics_classification_after_commit():
    _membership, bar, subject, observation = setup_signal_context()
    candidate = mojito_candidate(bar=bar, subject=subject)
    resolved = ResolvedTaxonomy(
        operational_unit=None,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=subject,
    )

    with patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay:
        signal = create_signal_from_candidate(
            observation=observation,
            candidate=candidate,
            resolved=resolved,
            title=candidate.title,
            structured_summary=candidate.structured_summary,
            routing_status=Signal.RoutingStatus.RESOLVED,
        )

    delay.assert_called_once_with(str(signal.id))


def test_aggregate_candidate_into_signal_does_not_schedule_analytics_classification():
    membership, _bar, _subject, observation = setup_signal_context()
    signal = Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Issue",
        structured_summary="Structured issue summary",
        last_activity_at=timezone.now(),
    )

    with patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay:
        aggregate_candidate_into_signal(signal=signal, observation=observation)

    delay.assert_not_called()


def test_qualify_signal_routing_schedules_reclassification_when_signature_changes():
    membership, bar, subject, _observation = setup_signal_context(
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_resolved_signal(membership, bar, subject, issue_focus="stock")

    with patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay:
        qualify_signal_routing(
            signal=signal,
            membership=membership,
            patch={"issue_focus": "new stock issue"},
        )

    delay.assert_called_once_with(str(signal.id))


def test_qualify_signal_routing_expected_action_only_does_not_reclassify():
    membership, bar, subject, _observation = setup_signal_context(
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = create_resolved_signal(membership, bar, subject)

    with patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay:
        qualify_signal_routing(
            signal=signal,
            membership=membership,
            patch={"expected_action": "inspect"},
        )

    delay.assert_not_called()


def test_qualify_signal_routing_business_unit_only_does_not_reclassify():
    membership, _bar, _subject, _observation = setup_signal_context(
        role=EstablishmentMembership.Role.OWNER,
    )
    signal = Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Unassigned",
        structured_summary="Needs qualification.",
        issue_focus="",
        last_activity_at=timezone.now(),
    )
    other = create_business_unit(
        establishment=membership.establishment,
        key="spa",
        label="Spa",
    )

    with patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay:
        qualify_signal_routing(
            signal=signal,
            membership=membership,
            patch={"affected_business_unit_id": other.id},
        )

    delay.assert_not_called()


def test_qualify_signal_routing_merge_does_not_reclassify_source_or_unchanged_survivor():
    membership, bar, subject, _observation = setup_signal_context(
        role=EstablishmentMembership.Role.OWNER,
    )
    focus = normalize_issue_focus("stock")
    survivor = create_resolved_signal(
        membership,
        bar,
        subject,
        title="Survivor",
        issue_focus=focus,
    )
    source = Signal.objects.create(
        establishment=membership.establishment,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        title="Source",
        structured_summary="Needs qualification.",
        issue_focus="",
        last_activity_at=timezone.now(),
    )

    with patch("houston.analytics.tasks.classify_signal_pattern_task.delay") as delay:
        qualify_signal_routing(
            signal=source,
            membership=membership,
            patch={
                "affected_business_unit_id": bar.id,
                "responsible_business_unit_id": bar.id,
                "activity_subject_id": subject.id,
                "issue_focus": focus,
            },
        )

    source.refresh_from_db()
    assert source.merged_into_id == survivor.id
    delay.assert_not_called()
