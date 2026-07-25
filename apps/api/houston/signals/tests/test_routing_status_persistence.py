from __future__ import annotations

import importlib

import pytest
from django.db import IntegrityError, transaction
from django.db.models import NOT_PROVIDED
from django.utils import timezone

from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.models import ExpectedAction, Signal
from houston.testing.factories import create_establishment


pytestmark = pytest.mark.django_db


def test_routing_status_field_has_no_permanent_default():
    field = Signal._meta.get_field("routing_status")
    assert field.default is NOT_PROVIDED
    assert field.has_default() is False


def test_expected_action_choices_match_v6_list():
    assert {choice.value for choice in ExpectedAction} == {
        "clean_secure",
        "repair",
        "replenish",
        "inspect",
        "coordinate",
        "assist",
        "inform",
        "monitor",
        "safety_response",
    }


def test_two_active_unassigned_signals_coexist_with_same_null_aggregation_key():
    establishment = create_establishment()
    now = timezone.now()
    Signal.objects.create(
        establishment=establishment,
        title="Unassigned A",
        structured_summary="Partial A.",
        issue_focus="same-focus",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=now,
    )
    Signal.objects.create(
        establishment=establishment,
        title="Unassigned B",
        structured_summary="Partial B.",
        issue_focus="same-focus",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=now,
    )
    assert (
        Signal.objects.filter(
            establishment=establishment,
            routing_status=Signal.RoutingStatus.UNASSIGNED,
        ).count()
        == 2
    )


def test_two_active_resolved_signals_with_same_key_raise_integrity_error():
    establishment = create_establishment()
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Menage",
    )
    now = timezone.now()
    kwargs = dict(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Resolved A",
        structured_summary="Resolved A.",
        issue_focus="same-focus",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.RESOLVED,
        last_activity_at=now,
    )
    Signal.objects.create(**kwargs)
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Signal.objects.create(
                **{
                    **kwargs,
                    "title": "Resolved B",
                    "structured_summary": "Resolved B.",
                }
            )


def test_backfill_routing_status_marks_coherent_triplet_resolved():
    migration_module = importlib.import_module(
        "houston.signals.migrations.0009_signal_routing_status_backfill"
    )
    establishment = create_establishment()
    hotel = create_business_unit(establishment=establishment, key="hotel", label="Hotel")
    subject = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Menage",
    )
    # Intentionally wrong statuses — backfill must correct from taxonomy fields.
    coherent = Signal.objects.create(
        establishment=establishment,
        affected_business_unit=hotel,
        responsible_business_unit=hotel,
        activity_subject=subject,
        title="Coherent",
        structured_summary="Coherent.",
        issue_focus="menage",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.UNASSIGNED,
        last_activity_at=timezone.now(),
    )
    partial = Signal.objects.create(
        establishment=establishment,
        affected_business_unit=hotel,
        title="Partial",
        structured_summary="Partial.",
        issue_focus="partial",
        status=Signal.Status.OPEN,
        routing_status=Signal.RoutingStatus.RESOLVED,
        last_activity_at=timezone.now(),
    )

    from django.apps import apps

    migration_module._backfill_signal_routing_status(apps, None)

    coherent.refresh_from_db()
    partial.refresh_from_db()
    assert coherent.routing_status == Signal.RoutingStatus.RESOLVED
    assert partial.routing_status == Signal.RoutingStatus.UNASSIGNED
