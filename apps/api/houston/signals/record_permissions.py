from houston.establishments.models import EstablishmentMembership
from houston.signals.permissions import _manager_or_admin_commandable


def can_manage_record(actor, signal):
    if actor and signal.record_kind == "project" and actor.role == "manager":
        from houston.establishments.membership_scope import membership_scope_covers_business_unit

        return bool(
            actor.status == "active"
            and actor.establishment_id == signal.establishment_id
            and signal.responsible_business_unit_id
            and membership_scope_covers_business_unit(actor, signal.responsible_business_unit)
        )
    return bool(
        actor
        and actor.status == EstablishmentMembership.Status.ACTIVE
        and actor.establishment_id == signal.establishment_id
        and _manager_or_admin_commandable(actor, signal)
    )


def can_progress_record(actor, signal):
    return can_manage_record(actor, signal) or bool(
        actor
        and actor.status == EstablishmentMembership.Status.ACTIVE
        and actor.establishment_id == signal.establishment_id
        and signal.status not in ("resolved", "canceled")
        and actor.id == signal.owner_membership_id
    )
