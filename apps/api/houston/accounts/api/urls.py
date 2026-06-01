from django.urls import path

from houston.accounts.api.views import (
    BootstrapView,
    CsrfCookieView,
    LoginView,
    LogoutView,
    RefreshView,
    RegisterView,
    SwitchEstablishmentView,
    ValidateOwnerRegistrationView,
)

urlpatterns = [
    path("csrf/", CsrfCookieView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path(
        "register/validate-owner/",
        ValidateOwnerRegistrationView.as_view(),
        name="auth-register-validate-owner",
    ),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("bootstrap/", BootstrapView.as_view(), name="auth-bootstrap"),
    path(
        "switch_establishment/",
        SwitchEstablishmentView.as_view(),
        name="auth-switch-establishment",
    ),
]
