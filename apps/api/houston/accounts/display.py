from __future__ import annotations

from houston.accounts.models import User

DELETED_ACCOUNT_DISPLAY_NAME = "Compte supprimé"


def user_display_name(user: User | None) -> str:
    if user is None:
        return DELETED_ACCOUNT_DISPLAY_NAME
    if user.status == User.Status.ANONYMIZED:
        return DELETED_ACCOUNT_DISPLAY_NAME
    return user.get_full_name() or user.email or user.username or DELETED_ACCOUNT_DISPLAY_NAME


def membership_display_name(membership) -> str | None:
    if membership is None:
        return None
    return user_display_name(membership.user)
