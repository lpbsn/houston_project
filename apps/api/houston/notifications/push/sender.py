from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from django.conf import settings
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from houston.notifications.models import PushDevice
from houston.notifications.push.exceptions import FcmSendError
from houston.notifications.push.payloads import stringify_push_data

logger = logging.getLogger(__name__)

FCM_SCOPES = ("https://www.googleapis.com/auth/firebase.messaging",)
FCM_REVOKE_ERROR_CODES = frozenset({"UNREGISTERED", "NOT_FOUND"})
HTTP_TIMEOUT_SECONDS = 15


def load_fcm_service_account() -> dict[str, Any] | None:
    raw = settings.HOUSTON_FCM_SERVICE_ACCOUNT_JSON.strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    project_id = payload.get("project_id")
    client_email = payload.get("client_email")
    private_key = payload.get("private_key")
    if not (
        isinstance(project_id, str)
        and project_id
        and isinstance(client_email, str)
        and client_email
        and isinstance(private_key, str)
        and private_key
    ):
        return None
    return payload


def is_fcm_configured() -> bool:
    return load_fcm_service_account() is not None


def log_fcm_not_configured(*, notification_id: str) -> None:
    logger.warning(
        "push_fcm_not_configured",
        extra={
            "event": "push_fcm_not_configured",
            "notification_id": notification_id,
        },
    )


def build_fcm_http_body(*, token: str, payload: dict) -> dict[str, Any]:
    return {
        "message": {
            "token": token,
            "notification": {
                "title": payload["title"],
                "body": payload["body"],
            },
            "data": stringify_push_data(payload["data"]),
        }
    }


def _fcm_error_from_http(*, status_code: int, body: bytes) -> FcmSendError:
    error_code = f"http_{status_code}" if status_code else "unknown"
    fcm_error_code = None
    try:
        parsed = json.loads(body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None
    if isinstance(parsed, dict):
        error = parsed.get("error")
        if isinstance(error, dict):
            status = error.get("status")
            if isinstance(status, str) and status:
                error_code = status.lower()
            details = error.get("details")
            if isinstance(details, list):
                for detail in details:
                    if not isinstance(detail, dict):
                        continue
                    candidate = detail.get("errorCode")
                    if isinstance(candidate, str) and candidate:
                        fcm_error_code = candidate
                        error_code = candidate.lower()
                        break
    should_revoke = fcm_error_code in FCM_REVOKE_ERROR_CODES or status_code in {404, 410}
    if status_code >= 500:
        error_code = "transient"
        should_revoke = False
    return FcmSendError(error_code=error_code, should_revoke=should_revoke)


def send_fcm(*, device: PushDevice, payload: dict) -> None:
    account = load_fcm_service_account()
    if account is None:
        raise FcmSendError(error_code="not_configured", should_revoke=False)

    credentials = service_account.Credentials.from_service_account_info(
        account,
        scopes=FCM_SCOPES,
    )
    credentials.refresh(Request())
    project_id = account["project_id"]
    url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
    body = json.dumps(build_fcm_http_body(token=device.token, payload=payload)).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        response_body = exc.read() if exc.fp is not None else b""
        raise _fcm_error_from_http(status_code=exc.code, body=response_body) from exc
    except urllib.error.URLError as exc:
        raise FcmSendError(error_code="unknown", should_revoke=False) from exc
