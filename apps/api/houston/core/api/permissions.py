from rest_framework.permissions import BasePermission


class DenyByDefault(BasePermission):
    """Fail closed when a view omits permission_classes."""

    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        return False
