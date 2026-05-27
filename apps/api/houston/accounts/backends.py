from __future__ import annotations

from django.contrib.auth.backends import ModelBackend

from houston.accounts.models import User


class IdentifierBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, identifier=None, **kwargs):
        login_identifier = identifier or username

        if not login_identifier or not password:
            return None

        if "@" in login_identifier:
            user = self._get_user_by_email(login_identifier)
        else:
            user = self._get_user_by_username(login_identifier)

        if user is None:
            User().set_password(password)
            return None

        if not user.check_password(password):
            return None

        if not self.user_can_authenticate(user):
            return None

        if user.status != User.Status.ACTIVE:
            return None

        return user

    def _get_user_by_email(self, identifier: str) -> User | None:
        normalized_email = User.normalize_email_value(identifier)

        if normalized_email is None:
            return None

        return User.objects.filter(email__iexact=normalized_email).first()

    def _get_user_by_username(self, identifier: str) -> User | None:
        return User.objects.filter(username=identifier).first()
