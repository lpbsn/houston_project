from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from houston.core.views import AppHomeView, HomeView

urlpatterns = [
    path("", include("houston.accounts.urls")),
    path("", HomeView.as_view(), name="home"),
    path("app/", AppHomeView.as_view(), name="app-home"),
    path("api/v1/", include("houston.core.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
]
