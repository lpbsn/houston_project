from django.urls import path
from houston.observations.api.media_views import ObservationMediaPreviewView
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
    path(
        "establishments/<uuid:establishment_id>/observation-media/<uuid:media_id>/preview/",
        ObservationMediaPreviewView.as_view(),
        name="observation-media-preview",
    ),
]
