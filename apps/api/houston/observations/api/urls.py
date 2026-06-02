from django.urls import path
from houston.observations.api.views import ObservationSubmitView

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/observations/",
        ObservationSubmitView.as_view(),
        name="observation-submit",
    ),
]
