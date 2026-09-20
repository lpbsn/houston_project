from __future__ import annotations

from houston.accounts.models import User
from houston.platform.models import PlatformOperatorAccess


def is_active_platform_operator(user: User | None) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.status != User.Status.ACTIVE:
        return False
    return PlatformOperatorAccess.objects.filter(user_id=user.pk, is_active=True).exists()
