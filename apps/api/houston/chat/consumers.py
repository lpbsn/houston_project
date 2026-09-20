from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from houston.chat.groups import membership_group_name, session_group_name
from houston.chat.selectors import get_active_participant
from houston.chat.ws_access import WsAccessValidation, validate_ws_connection_access
from houston.chat.ws_payloads import (
    build_membership_access_revoked_payload,
)
from houston.chat.ws_ticket import WsTicketError, consume_ws_ticket
from houston.core.observability import build_ws_auth_failure_log_context

logger = logging.getLogger(__name__)

WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_FORBIDDEN = 4002
WS_CLOSE_CHAT_DISABLED = 4003
WS_CLOSE_TENANT_INVALID = 4004
WS_CLOSE_PROTOCOL_ERROR = 4400
WS_CLOSE_AUTH_TIMEOUT = 4408


class ChatConsumer(AsyncWebsocketConsumer):
    establishment_id: UUID
    authenticated = False
    membership_id: UUID | None = None
    session_id: UUID | None = None
    auth_timeout_task: asyncio.Task | None = None

    async def connect(self) -> None:
        raw_establishment_id = self.scope["url_route"]["kwargs"].get("establishment_id")
        try:
            self.establishment_id = UUID(str(raw_establishment_id))
        except (TypeError, ValueError):
            await self.close(code=WS_CLOSE_TENANT_INVALID)
            return

        await self.accept()
        self.auth_timeout_task = asyncio.create_task(self._enforce_auth_timeout())

    async def disconnect(self, close_code: int) -> None:
        if self.auth_timeout_task is not None:
            self.auth_timeout_task.cancel()
            self.auth_timeout_task = None

        if self.membership_id is not None:
            await self.channel_layer.group_discard(
                membership_group_name(
                    establishment_id=self.establishment_id,
                    membership_id=self.membership_id,
                ),
                self.channel_name,
            )

        if self.session_id is not None:
            await self.channel_layer.group_discard(
                session_group_name(session_id=self.session_id),
                self.channel_name,
            )

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is None:
            await self._send_error(code="validation_error", detail="Expected a JSON text frame.")
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error(code="validation_error", detail="Invalid JSON payload.")
            return

        if not isinstance(payload, dict):
            await self._send_error(code="validation_error", detail="Invalid JSON payload.")
            return

        message_type = payload.get("type")
        if not self.authenticated:
            if message_type != "auth":
                await self.close(code=WS_CLOSE_AUTH_FAILED)
                return
            await self._handle_auth(payload)
            return

        if not await self._ensure_authorized():
            return

        if message_type == "message.send":
            logger.warning(
                "chat_ws_message_send_rejected",
                extra={
                    "event": "chat_ws_message_send_rejected",
                    "establishment_id": str(self.establishment_id),
                    "membership_id": str(self.membership_id) if self.membership_id else None,
                },
            )
            await self._send_error(
                code="protocol_error",
                detail="Message send is HTTP-only. WebSocket is events only.",
            )
            await self.close(code=WS_CLOSE_PROTOCOL_ERROR)
            return

        await self._send_error(code="validation_error", detail="Unsupported message type.")

    async def chat_message_created(self, event: dict) -> None:
        await self._deliver_conversation_payload_if_participant(event)

    async def chat_conversation_updated(self, event: dict) -> None:
        await self._deliver_conversation_payload_if_participant(event)

    async def chat_conversation_access_revoked(self, event: dict) -> None:
        if not await self._ensure_authorized():
            return
        await self.send(text_data=json.dumps(event["payload"]))

    async def chat_membership_access_revoked(self, event: dict) -> None:
        await self._revoke_access_and_close(event["payload"].get("reason", "access_denied"))

    async def chat_session_access_revoked(self, event: dict) -> None:
        await self._revoke_access_and_close(event["payload"].get("reason", "access_denied"))

    async def _enforce_auth_timeout(self) -> None:
        try:
            await asyncio.sleep(settings.HOUSTON_CHAT_WS_AUTH_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return
        if not self.authenticated:
            logger.warning(
                "chat_ws_auth_failed",
                extra=build_ws_auth_failure_log_context(
                    establishment_id=self.establishment_id,
                    reason="auth_timeout",
                    close_code=WS_CLOSE_AUTH_TIMEOUT,
                ),
            )
            await self.close(code=WS_CLOSE_AUTH_TIMEOUT)

    async def _handle_auth(self, payload: dict) -> None:
        ticket = payload.get("ticket")
        if not isinstance(ticket, str) or not ticket.strip():
            await self._close_auth_failed(reason="missing_ticket")
            return

        try:
            ticket_payload = consume_ws_ticket(
                ticket.strip(),
                establishment_id=self.establishment_id,
            )
        except WsTicketError:
            await self._close_auth_failed(reason="invalid_ticket")
            return

        access = await self._validate_ticket_access(
            session_id=ticket_payload.session_id,
            membership_id=ticket_payload.membership_id,
        )
        if not access.ok:
            reason = access.reason or "access_denied"
            await self._close_ws_auth(
                reason=self._auth_log_reason(reason),
                close_code=self._auth_close_code(reason),
            )
            return

        self.authenticated = True
        self.membership_id = ticket_payload.membership_id
        self.session_id = ticket_payload.session_id
        if self.auth_timeout_task is not None:
            self.auth_timeout_task.cancel()
            self.auth_timeout_task = None

        await self.channel_layer.group_add(
            membership_group_name(
                establishment_id=self.establishment_id,
                membership_id=self.membership_id,
            ),
            self.channel_name,
        )
        await self.channel_layer.group_add(
            session_group_name(session_id=self.session_id),
            self.channel_name,
        )

        await self.send(
            text_data=json.dumps(
                {
                    "type": "auth.ok",
                    "user_id": str(ticket_payload.user_id),
                    "membership_id": str(ticket_payload.membership_id),
                    "session_id": str(ticket_payload.session_id),
                }
            )
        )

    async def _ensure_authorized(self) -> bool:
        access = await self._validate_ws_access()
        if access.ok:
            return True
        await self._revoke_access_and_close(access.reason or "access_denied")
        return False

    async def _deliver_conversation_payload_if_participant(self, event: dict) -> None:
        if not await self._ensure_authorized():
            return
        if self.membership_id is None:
            return

        payload = event.get("payload")
        if not isinstance(payload, dict):
            return
        conversation_id = self._parse_uuid(payload.get("conversation_id"))
        if conversation_id is None:
            return

        participant = await self._load_active_participant(conversation_id)
        if participant is None:
            return

        await self.send(text_data=json.dumps(payload))

    @database_sync_to_async
    def _validate_ws_access(self):
        if self.session_id is None or self.membership_id is None:
            return WsAccessValidation(ok=False, reason="access_denied")

        return validate_ws_connection_access(
            session_id=self.session_id,
            establishment_id=self.establishment_id,
            membership_id=self.membership_id,
        )

    @database_sync_to_async
    def _validate_ticket_access(self, *, session_id: UUID, membership_id: UUID):
        return validate_ws_connection_access(
            session_id=session_id,
            establishment_id=self.establishment_id,
            membership_id=membership_id,
        )

    @database_sync_to_async
    def _load_active_participant(self, conversation_id: UUID):
        return get_active_participant(
            conversation_id=conversation_id,
            membership_id=self.membership_id,
        )

    async def _revoke_access_and_close(self, reason: str) -> None:
        await self.send(
            text_data=json.dumps(build_membership_access_revoked_payload(reason=reason))
        )
        self.authenticated = False
        await self.close(code=WS_CLOSE_FORBIDDEN)

    @staticmethod
    def _parse_uuid(raw_value) -> UUID | None:
        if raw_value is None:
            return None
        try:
            return UUID(str(raw_value))
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def _auth_close_code(reason: str) -> int:
        if reason == "session_revoked":
            return WS_CLOSE_AUTH_FAILED
        if reason == "chat_disabled":
            return WS_CLOSE_CHAT_DISABLED
        return WS_CLOSE_FORBIDDEN

    @staticmethod
    def _auth_log_reason(reason: str) -> str:
        if reason == "session_revoked":
            return "invalid_session"
        if reason == "chat_disabled":
            return "chat_disabled"
        if reason == "establishment_switched":
            return "establishment_switched"
        return "forbidden"

    async def _send_error(self, *, code: str, detail: str) -> None:
        await self.send(text_data=json.dumps({"type": "error", "code": code, "detail": detail}))

    async def _close_auth_failed(self, *, reason: str) -> None:
        await self._close_ws_auth(reason=reason, close_code=WS_CLOSE_AUTH_FAILED)

    async def _close_ws_auth(self, *, reason: str, close_code: int) -> None:
        logger.warning(
            "chat_ws_auth_failed",
            extra=build_ws_auth_failure_log_context(
                establishment_id=self.establishment_id,
                reason=reason,
                close_code=close_code,
            ),
        )
        await self.close(code=close_code)
