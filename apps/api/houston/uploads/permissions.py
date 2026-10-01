from __future__ import annotations

from rest_framework.permissions import BasePermission

from houston.establishments.access import get_api_access_context
from houston.establishments.permissions import can_create_observation
from houston.uploads.preview_tokens import unsign_upload_preview_token


class CanSubmitObservation(BasePermission):
    message = "You do not have permission to submit observations for this establishment."

    def has_permission(self, request, view) -> bool:
        access_context = get_api_access_context(request)
        establishment_id = getattr(view, "establishment_id", None)
        if establishment_id is None:
            return False
        membership = access_context.membership_for_establishment(establishment_id)
        if membership is None:
            return False
        return can_create_observation(membership)


class IsAuthenticatedOrSignedUploadPreviewToken(BasePermission):
    """Credential gate for private previews that accept a bearer or a signed viewer token.

    The view sets ``preview_token_salt``. Membership, establishment, and history checks
    stay on the view so a signed-but-unauthorized token still resolves there.
    """

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False):
            return True
        salt = getattr(view, "preview_token_salt", None)
        if not salt:
            return False
        token = (request.query_params.get("token") or "").strip()
        if not token:
            return False
        return unsign_upload_preview_token(salt=salt, token=token) is not None
