from __future__ import annotations

from django.utils import timezone

from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.models import Signal


def create_signal_for_membership(membership, *, title="Clim en panne"):
    bar = create_business_unit(
        establishment=membership.establishment,
        key="bar",
        label="Bar",
    )
    maintenance = create_business_unit(
        establishment=membership.establishment,
        key="maintenance",
        label="Maintenance",
    )
    subject = create_activity_subject(
        establishment=membership.establishment,
        business_unit=maintenance,
        label="Equipment",
    )
    return Signal.objects.create(
        establishment=membership.establishment,
        affected_business_unit=bar,
        responsible_business_unit=maintenance,
        activity_subject=subject,
        routing_status=Signal.RoutingStatus.RESOLVED,
        title=title,
        structured_summary="La climatisation ne fonctionne plus dans la chambre.",
        issue_focus="climatisation",
        last_activity_at=timezone.now(),
    )
