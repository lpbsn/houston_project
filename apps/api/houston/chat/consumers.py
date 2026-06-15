from __future__ import annotations

import asyncio
import json
import logging
from uuid import UUID

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.utils import timezone
from houston.accounts.models import User, UserSession
from houston.chat.exceptions import (
    ChatError,
    ChatNotFoundError,
    ChatPermissionError,
    ChatValidationError,
)
from houston.chat.groups import membership_group_name, session_group_name
from houston.chat.permissions import can_access_chat
from houston.chat.rate_limits import ChatMessageRateLimitExceeded, check_message_send_rate_limit
from houston.chat.services import MessageSendResult, create_message
from houston.chat.ws_access import WsAccessValidation, validate_ws_connection_access
from houston.chat.ws_payloads import (
    build_membership_access_revoked_payload,
    build_message_created_payload,
    build_message_rejected_payload,
)
from houston.chat.ws_ticket import WsTicketError, WsTicketPayload, consume_ws_ticket
from houston.core.observability import build_ws_auth_failure_log_context
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization

logger = logging.getLogger(__name__)

WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_FORBIDDEN = 4002
WS_CLOSE_CHAT_DISABLED = 4003
WS_CLOSE_TENANT_INVALID = 4004
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

        if self.authenticated and self.membership_id is not None:
            await self.channel_layer.group_discard(
                membership_group_name(
                    establishment_id=self.establishment_id,
                    membership_id=self.membership_id,
                ),
                self.channel_name,
            )

        if self.authenticated and self.session_id is not None:
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

        if message_type == "message.send":
            await self._handle_message_send(payload)
            return

        await self._send_error(code="validation_error", detail="Unsupported message type.")

    async def chat_message_created(self, event: dict) -> None:
        await self.send(text_data=json.dumps(event["payload"]))

    async def chat_conversation_access_revoked(self, event: dict) -> None:
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

        if not await self._is_ticket_session_valid(ticket_payload):
            await self._close_auth_failed(reason="invalid_session")
            return

        membership = await self._load_membership(ticket_payload.membership_id)
        if membership is None:
            await self._close_ws_auth(
                reason="membership_not_found",
                close_code=WS_CLOSE_FORBIDDEN,
            )
            return

        if membership.user_id != ticket_payload.user_id:
            await self._close_ws_auth(
                reason="forbidden",
                close_code=WS_CLOSE_FORBIDDEN,
            )
            return

        if membership.establishment_id != self.establishment_id:
            await self._close_ws_auth(
                reason="tenant_mismatch",
                close_code=WS_CLOSE_TENANT_INVALID,
            )
            return

        if not can_access_chat(membership):
            close_code = (
                WS_CLOSE_CHAT_DISABLED
                if membership.establishment.status == Establishment.Status.ACTIVE
                and not membership.establishment.chat_enabled
                else WS_CLOSE_FORBIDDEN
            )
            reason = "chat_disabled" if close_code == WS_CLOSE_CHAT_DISABLED else "forbidden"
            await self._close_ws_auth(reason=reason, close_code=close_code)
            return

        self.authenticated = True
        self.membership_id = membership.id
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
                    "user_id": str(membership.user_id),
                    "membership_id": str(membership.id),
                    "session_id": str(ticket_payload.session_id),
                }
            )
        )

    async def _handle_message_send(self, payload: dict) -> None:
        if self.membership_id is None or self.session_id is None:
            await self.close(code=WS_CLOSE_FORBIDDEN)
            return

        access = await self._validate_ws_access()
        if not access.ok:
            await self._revoke_access_and_close(access.reason or "access_denied")
            return

        raw_conversation_id = payload.get("conversation_id")
        raw_client_message_id = payload.get("client_message_id")
        body = payload.get("body")

        conversation_id = self._parse_uuid(raw_conversation_id)
        client_message_id = self._parse_uuid(raw_client_message_id)
        if conversation_id is None or client_message_id is None:
            await self._send_message_rejected(
                client_message_id=client_message_id,
                code="validation_error",
                detail="Invalid message.send payload.",
            )
            return
        if not isinstance(body, str):
            await self._send_message_rejected(
                client_message_id=client_message_id,
                code="validation_error",
                detail="Invalid message.send payload.",
            )
            return

        try:
            result = await self._persist_message(
                conversation_id=conversation_id,
                client_message_id=client_message_id,
                body=body,
            )
        except ChatValidationError as exc:
            code = "throttled" if "rate limit" in exc.message.lower() else exc.code
            await self._send_message_rejected(
                client_message_id=client_message_id,
                code=code,
                detail=exc.message,
            )
            return
        except ChatPermissionError as exc:
            await self._send_message_rejected(
                client_message_id=client_message_id,
                code=exc.code,
                detail=exc.message,
            )
            return
        except ChatNotFoundError:
            await self._send_message_rejected(
                client_message_id=client_message_id,
                code="permission_denied",
                detail="You do not have permission to send messages in this conversation.",
            )
            return
        except ChatError as exc:
            await self._send_message_rejected(
                client_message_id=client_message_id,
                code=exc.code,
                detail=exc.message,
            )
            return

        created_payload = build_message_created_payload(
            conversation_id=conversation_id,
            message=result.message,
        )
        if result.created:
            await self._broadcast_message_created(
                result=result,
                payload=created_payload,
            )
        else:
            await self.send(text_data=json.dumps(created_payload))

    async def _broadcast_message_created(
        self,
        *,
        result: MessageSendResult,
        payload: dict,
    ) -> None:
        for recipient_membership_id in result.recipient_membership_ids:
            await self.channel_layer.group_send(
                membership_group_name(
                    establishment_id=self.establishment_id,
                    membership_id=recipient_membership_id,
                ),
                {
                    "type": "chat.message.created",
                    "payload": payload,
                },
            )

    @database_sync_to_async
    def _validate_ws_access(self):
        if self.session_id is None or self.membership_id is None:
            return WsAccessValidation(ok=False, reason="access_denied")

        return validate_ws_connection_access(
            session_id=self.session_id,
            establishment_id=self.establishment_id,
            membership_id=self.membership_id,
        )

    async def _revoke_access_and_close(self, reason: str) -> None:
        await self.send(
            text_data=json.dumps(build_membership_access_revoked_payload(reason=reason))
        )
        self.authenticated = False
        await self.close(code=WS_CLOSE_FORBIDDEN)

    @database_sync_to_async
    def _persist_message(
        self,
        *,
        conversation_id: UUID,
        client_message_id: UUID,
        body: str,
    ) -> MessageSendResult:
        membership = (
            EstablishmentMembership.objects.select_related(
                "user",
                "establishment",
                "establishment__organization",
            )
            .filter(
                id=self.membership_id,
                status=EstablishmentMembership.Status.ACTIVE,
                user__status=User.Status.ACTIVE,
                establishment_id=self.establishment_id,
                establishment__status=Establishment.Status.ACTIVE,
                establishment__organization__status=Organization.Status.ACTIVE,
            )
            .first()
        )
        if membership is None or not can_access_chat(membership):
            raise ChatPermissionError()

        try:
            check_message_send_rate_limit(
                establishment_id=self.establishment_id,
                membership_id=membership.id,
            )
        except ChatMessageRateLimitExceeded as exc:
            raise ChatValidationError("Message send rate limit exceeded.") from exc

        return create_message(
            author_membership=membership,
            establishment_id=self.establishment_id,
            conversation_id=conversation_id,
            client_message_id=client_message_id,
            body=body,
        )

    @staticmethod
    def _parse_uuid(raw_value) -> UUID | None:
        if raw_value is None:
            return None
        try:
            return UUID(str(raw_value))
        except (TypeError, ValueError, AttributeError):
            return None

    @database_sync_to_async
    def _is_ticket_session_valid(self, ticket_payload: WsTicketPayload) -> bool:
        session = UserSession.objects.filter(id=ticket_payload.session_id).first()
        if session is None:
            return False
        if session.user_id != ticket_payload.user_id:
            return False
        now = timezone.now()
        if session.revoked_at is not None or session.status != UserSession.Status.ACTIVE:
            return False
        return session.absolute_expires_at > now

    @database_sync_to_async
    def _load_membership(self, membership_id: UUID) -> EstablishmentMembership | None:
        return (
            EstablishmentMembership.objects.select_related(
                "user",
                "establishment",
                "establishment__organization",
            )
            .filter(
                id=membership_id,
                status=EstablishmentMembership.Status.ACTIVE,
                user__status=User.Status.ACTIVE,
                establishment__status=Establishment.Status.ACTIVE,
                establishment__organization__status=Organization.Status.ACTIVE,
            )
            .first()
        )

    async def _send_message_rejected(
        self,
        *,
        client_message_id: UUID | None,
        code: str,
        detail: str,
    ) -> None:
        await self.send(
            text_data=json.dumps(
                build_message_rejected_payload(
                    client_message_id=client_message_id,
                    code=code,
                    detail=detail,
                )
            )
        )

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
