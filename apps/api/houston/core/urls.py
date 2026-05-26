from django.urls import path

from houston.core.views import HealthView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
]
