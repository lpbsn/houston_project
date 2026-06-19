from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from houston.core.views import AppHomeView, HomeView

urlpatterns = [
    path("", include("houston.accounts.urls")),
    path("", HomeView.as_view(), name="home"),
    path("app/", AppHomeView.as_view(), name="app-home"),
    path("api/v1/auth/", include("houston.accounts.api.urls")),
    path("api/v1/", include("houston.core.urls")),
    path("api/v1/", include("houston.establishments.api.urls")),
    path("api/v1/", include("houston.uploads.api.urls")),
    path("api/v1/", include("houston.observations.api.urls")),
    path("api/v1/", include("houston.signals.api.urls")),
    path("api/v1/", include("houston.actions.api.urls")),
    path("api/v1/", include("houston.checklists.api.urls")),
    path("api/v1/", include("houston.chat.api.urls")),
    path("api/v1/", include("houston.realtime.api.urls")),
    path("api/v1/", include("houston.comments.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
]
