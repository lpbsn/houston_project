from __future__ import annotations


class ObservationServiceError(Exception):
    error_code = "observation_error"


class ObservationValidationError(ObservationServiceError):
    error_code = "observation_validation_error"


class ObservationUploadNotFoundError(ObservationServiceError):
    error_code = "observation_upload_not_found"
