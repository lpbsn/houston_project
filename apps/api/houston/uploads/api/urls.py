from django.urls import path
from houston.uploads.api.transcription_views import TranscriptionCreateView
from houston.uploads.api.views import TemporaryUploadDeleteView, TemporaryUploadListCreateView

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/temporary-uploads/",
        TemporaryUploadListCreateView.as_view(),
        name="temporary-upload-list-create",
    ),
    path(
        "establishments/<uuid:establishment_id>/temporary-uploads/<uuid:upload_id>/",
        TemporaryUploadDeleteView.as_view(),
        name="temporary-upload-delete",
    ),
    path(
        "establishments/<uuid:establishment_id>/transcriptions/",
        TranscriptionCreateView.as_view(),
        name="transcription-create",
    ),
]
