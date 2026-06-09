from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from django.core.cache import cache, caches
from django.utils.crypto import salted_hmac
from houston.accounts.tokens import generate_raw_token
from houston.establishments.models import EstablishmentMembership


class WsTicketError(Exception):
    def __init__(self, *, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class WsTicketPayload:
    user_id: UUID
    session_id: UUID
    establishment_id: UUID
    membership_id: UUID


def _ticket_cache_key(raw_ticket: str) -> str:
    digest = salted_hmac(
        settings.HOUSTON_CHAT_WS_TICKET_SALT,
        raw_ticket,
        secret=settings.HOUSTON_AUTH_TOKEN_PEPPER,
        algorithm="sha256",
    ).hexdigest()
    return f"chat:ws_ticket:{digest}"


def _serialize_payload(payload: WsTicketPayload) -> str:
    return json.dumps(
        {
            "user_id": str(payload.user_id),
            "session_id": str(payload.session_id),
            "establishment_id": str(payload.establishment_id),
            "membership_id": str(payload.membership_id),
        }
    )


def _deserialize_payload(raw: str) -> WsTicketPayload:
    data = json.loads(raw)
    return WsTicketPayload(
        user_id=UUID(data["user_id"]),
        session_id=UUID(data["session_id"]),
        establishment_id=UUID(data["establishment_id"]),
        membership_id=UUID(data["membership_id"]),
    )


def issue_ws_ticket(
    *,
    membership: EstablishmentMembership,
    session_id: UUID,
) -> tuple[str, int]:
    raw_ticket = generate_raw_token()
    payload = WsTicketPayload(
        user_id=membership.user_id,
        session_id=session_id,
        establishment_id=membership.establishment_id,
        membership_id=membership.id,
    )
    cache.set(
        _ticket_cache_key(raw_ticket),
        _serialize_payload(payload),
        timeout=settings.HOUSTON_CHAT_WS_TICKET_TTL_SECONDS,
    )
    return raw_ticket, settings.HOUSTON_CHAT_WS_TICKET_TTL_SECONDS


def _atomic_pop_ticket_payload(cache_key: str) -> str | None:
    """Remove and return ticket payload in one step (GETDEL on Redis in prod)."""
    backend = caches["default"]
    if not hasattr(backend, "client"):
        cached = backend.get(cache_key)
        if cached is not None:
            backend.delete(cache_key)
        return cached

    client_wrapper = backend.client
    redis_client = client_wrapper.get_client(write=True)
    redis_key = client_wrapper.make_key(cache_key)
    if hasattr(redis_client, "getdel"):
        raw = redis_client.getdel(redis_key)
    else:
        raw = redis_client.eval(
            "local value = redis.call('GET', KEYS[1]); "
            "if value then redis.call('DEL', KEYS[1]) end; "
            "return value",
            1,
            redis_key,
        )
    if raw is None:
        return None
    return client_wrapper.decode(raw)


def consume_ws_ticket(
    raw_ticket: str,
    *,
    establishment_id: UUID,
) -> WsTicketPayload:
    if not raw_ticket or not isinstance(raw_ticket, str):
        raise WsTicketError(code="authentication_failed", detail="Invalid WebSocket ticket.")

    cache_key = _ticket_cache_key(raw_ticket)
    cached = _atomic_pop_ticket_payload(cache_key)
    if cached is None:
        raise WsTicketError(code="authentication_failed", detail="Invalid WebSocket ticket.")

    try:
        payload = _deserialize_payload(cached)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise WsTicketError(
            code="authentication_failed",
            detail="Invalid WebSocket ticket.",
        ) from exc

    if payload.establishment_id != establishment_id:
        raise WsTicketError(code="authentication_failed", detail="Invalid WebSocket ticket.")

    return payload
