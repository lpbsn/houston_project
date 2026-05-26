from django import forms
from django.contrib.auth.forms import AuthenticationForm

from houston.accounts.models import User


class HoustonAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "inactive_status": "This account does not have access to the Houston app.",
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if user.status != User.Status.ACTIVE:
            raise forms.ValidationError(
                self.error_messages["inactive_status"],
                code="inactive_status",
            )
