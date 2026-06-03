from django.urls import path
from houston.observations.api.views import (
    ObservationProcessingStatusView,
    ObservationSubmitView,
)

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/observations/",
        ObservationSubmitView.as_view(),
        name="observation-submit",
    ),
    path(
        "establishments/<uuid:establishment_id>/observations/<uuid:observation_id>/processing-status/",
        ObservationProcessingStatusView.as_view(),
        name="observation-processing-status",
    ),
]
