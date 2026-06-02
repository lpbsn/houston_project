from __future__ import annotations

from rest_framework.permissions import BasePermission

from houston.establishments.access import get_api_access_context
from houston.establishments.permissions import can_create_observation


class CanSubmitObservation(BasePermission):
    message = "You do not have permission to submit observations for this establishment."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        membership = access_context.active_membership
        if membership is None:
            return False
        establishment_id = getattr(view, "establishment_id", None)
        if establishment_id is None:
            return False
        if str(membership.establishment_id) != str(establishment_id):
            return False
        return can_create_observation(membership)
