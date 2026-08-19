from __future__ import annotations

from houston.notifications.push.exceptions import FcmSendError
from houston.notifications.push.sender import _fcm_error_from_http


def test_fcm_unregistered_error_revokes():
    error = _fcm_error_from_http(
        status_code=404,
        body=b'{"error":{"status":"NOT_FOUND","details":[{"errorCode":"UNREGISTERED"}]}}',
    )
    assert isinstance(error, FcmSendError)
    assert error.error_code == "unregistered"
    assert error.should_revoke is True


def test_fcm_http_410_revokes():
    error = _fcm_error_from_http(status_code=410, body=b"{}")
    assert error.should_revoke is True
    assert error.error_code == "http_410"


def test_fcm_transient_5xx_does_not_revoke():
    error = _fcm_error_from_http(status_code=503, body=b"{}")
    assert error.error_code == "transient"
    assert error.should_revoke is False
