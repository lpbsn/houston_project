from __future__ import annotations

from houston.accounts.models import User
from houston.platform.services import grant_platform_operator


def grant_operator(user: User):
    return grant_platform_operator(user=user)
