from __future__ import annotations

from rest_framework.permissions import BasePermission

from houston.platform.selectors import is_active_platform_operator


class IsActivePlatformOperator(BasePermission):
    message = "Active Spore Platform operator access is required."

    def has_permission(self, request, view) -> bool:
        return is_active_platform_operator(getattr(request, "user", None))
