from __future__ import annotations

from houston.action_plans.api.views import ActionPlanExecutionTaskCreateObservationView
from houston.observations.api.views import ObservationSubmitView
from houston.uploads.api.transcription_views import TranscriptionCreateView


def test_observation_submit_and_transcription_have_no_admission_throttle():
    for view_class in (
        ObservationSubmitView,
        ActionPlanExecutionTaskCreateObservationView,
        TranscriptionCreateView,
    ):
        assert view_class().get_throttles() == []
        assert not getattr(view_class, "throttle_scope", "")
