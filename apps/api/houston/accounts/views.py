from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy

from houston.accounts.forms import HoustonAuthenticationForm


class HoustonLoginView(LoginView):
    authentication_form = HoustonAuthenticationForm
    next_page = reverse_lazy("app-home")
    redirect_authenticated_user = True
    template_name = "registration/login.html"


class HoustonLogoutView(LogoutView):
    http_method_names = ["post", "options"]
    next_page = reverse_lazy("login")
