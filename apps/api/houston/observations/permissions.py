from __future__ import annotations

from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.observations.models import Observation


def can_view_observation_processing_status(
    membership: EstablishmentMembership,
    observation: Observation,
) -> bool:
    if observation.establishment_id != membership.establishment_id:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return observation.submitted_by_membership_id == membership.id
