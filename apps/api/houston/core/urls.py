from django.urls import path

from houston.core.views import ClientRequirementsView, HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("client-requirements/", ClientRequirementsView.as_view(), name="client-requirements"),
]
