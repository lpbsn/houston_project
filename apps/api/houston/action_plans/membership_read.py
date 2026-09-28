from __future__ import annotations

from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES


def prepare_execution_read_membership(
    membership: EstablishmentMembership,
) -> EstablishmentMembership:
    """Reload a non-admin membership with establishment and scope prefetch.

    Admin roles skip the reload. Query shape is the previous per-feed helper.
    """
    if membership.role in ADMIN_ROLES:
        return membership
    return (
        EstablishmentMembership.objects.filter(pk=membership.pk)
        .select_related("establishment")
        .prefetch_related(membership_scope_prefetch())
        .get()
    )
