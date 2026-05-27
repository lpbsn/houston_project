from django.urls import path

from houston.accounts.api.views import (
    BootstrapView,
    CsrfCookieView,
    LoginView,
    LogoutView,
    RefreshView,
)

urlpatterns = [
    path("csrf/", CsrfCookieView.as_view(), name="auth-csrf"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("bootstrap/", BootstrapView.as_view(), name="auth-bootstrap"),
]
