from __future__ import annotations


class UploadServiceError(Exception):
    error_code = "upload_error"


class UploadNotFoundError(UploadServiceError):
    error_code = "upload_not_found"


class UploadNotDeletableError(UploadServiceError):
    error_code = "upload_not_deletable"
