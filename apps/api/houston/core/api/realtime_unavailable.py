from __future__ import annotations

import logging

import redis.exceptions
from rest_framework import exceptions, status

from houston.core.observability import build_api_request_log_context

logger = logging.getLogger(__name__)

REALTIME_UNAVAILABLE_CODE = "realtime_unavailable"
REALTIME_UNAVAILABLE_DETAIL = "Realtime is temporarily unavailable."
REALTIME_UNAVAILABLE_RETRY_AFTER_SECONDS = 2

_REDIS_UNAVAILABLE = (
    redis.exceptions.ConnectionError,
    redis.exceptions.TimeoutError,
)


class RealtimeUnavailable(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = REALTIME_UNAVAILABLE_DETAIL
    default_code = REALTIME_UNAVAILABLE_CODE

    def __init__(self) -> None:
        super().__init__()
        # DRF copies APIException.wait into the Retry-After header.
        self.wait = REALTIME_UNAVAILABLE_RETRY_AFTER_SECONDS


# Redis errors from DRF throttling (APIView.initial, before the handler) and from
# issue_ws_ticket both reach dispatch, which calls handle_exception.
class WsTicketRedisFailureMixin:
    def handle_exception(self, exc):
        if isinstance(exc, _REDIS_UNAVAILABLE):
            request = getattr(self, "request", None)
            logger.warning(
                "ws_ticket_realtime_unavailable",
                extra=build_api_request_log_context(
                    request_path=getattr(request, "path", "") if request is not None else "",
                    request_method=getattr(request, "method", "") if request is not None else "",
                    event="ws_ticket_realtime_unavailable",
                    exception_class=type(exc).__name__,
                ),
            )
            exc = RealtimeUnavailable()
        return super().handle_exception(exc)
