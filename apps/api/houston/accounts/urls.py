from django.urls import path

from houston.accounts.views import HoustonLoginView, HoustonLogoutView

urlpatterns = [
    path("login/", HoustonLoginView.as_view(), name="login"),
    path("logout/", HoustonLogoutView.as_view(), name="logout"),
]
