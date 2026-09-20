from __future__ import annotations

from django.utils import timezone

from houston.organizations.models import Organization


def mark_organization_has_been_operational(organization: Organization) -> Organization:
    """Sticky True once an establishment is activated. Never cleared."""
    if organization.has_been_operational:
        return organization
    now = timezone.now()
    updated = Organization.objects.filter(
        pk=organization.pk,
        has_been_operational=False,
    ).update(has_been_operational=True, updated_at=now)
    if updated:
        organization.has_been_operational = True
        organization.updated_at = now
    else:
        organization.refresh_from_db(fields=["has_been_operational", "updated_at"])
    return organization
