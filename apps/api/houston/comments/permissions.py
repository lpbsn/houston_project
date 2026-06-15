from __future__ import annotations

import uuid

from houston.comments.selectors import get_action_for_comments, get_signal_for_comments
from houston.establishments.models import EstablishmentMembership


def can_access_signal_comments(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> bool:
    return get_signal_for_comments(membership=membership, signal_id=signal_id) is not None


def can_access_action_comments(
    *,
    membership: EstablishmentMembership,
    action_id: uuid.UUID,
) -> bool:
    return get_action_for_comments(membership=membership, action_id=action_id) is not None
