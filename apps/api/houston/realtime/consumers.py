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
from houston.core.observability import build_ws_auth_failure_log_context
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.organizations.models import Organization
from houston.realtime.groups import (
    establishment_group_name,
    membership_group_name,
    session_group_name,
)
from houston.realtime.permissions import can_access_operational_realtime
from houston.realtime.ws_payloads import build_auth_ok_payload
from houston.realtime.ws_ticket import WsTicketError, WsTicketPayload, consume_ws_ticket

logger = logging.getLogger(__name__)

WS_CLOSE_AUTH_FAILED = 4001
WS_CLOSE_FORBIDDEN = 4002
WS_CLOSE_TENANT_INVALID = 4004
WS_CLOSE_AUTH_TIMEOUT = 4408


class RealtimeConsumer(AsyncWebsocketConsumer):
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
                establishment_group_name(establishment_id=self.establishment_id),
                self.channel_name,
            )
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
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.close(code=WS_CLOSE_AUTH_FAILED)
            return

        if not isinstance(payload, dict):
            await self.close(code=WS_CLOSE_AUTH_FAILED)
            return

        message_type = payload.get("type")
        if not self.authenticated:
            if message_type != "auth":
                await self.close(code=WS_CLOSE_AUTH_FAILED)
                return
            await self._handle_auth(payload)
            return

    async def realtime_invalidation(self, event: dict) -> None:
        await self.send(text_data=json.dumps(event["payload"]))

    async def realtime_access(self, event: dict) -> None:
        await self.send(text_data=json.dumps(event["payload"]))
        await self._close_after_access_event(event["payload"])

    async def _enforce_auth_timeout(self) -> None:
        try:
            await asyncio.sleep(settings.HOUSTON_REALTIME_WS_AUTH_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return
        if not self.authenticated:
            logger.warning(
                "realtime_ws_auth_failed",
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

        if not can_access_operational_realtime(membership):
            await self._close_ws_auth(
                reason="forbidden",
                close_code=WS_CLOSE_FORBIDDEN,
            )
            return

        self.authenticated = True
        self.membership_id = membership.id
        self.session_id = ticket_payload.session_id
        if self.auth_timeout_task is not None:
            self.auth_timeout_task.cancel()
            self.auth_timeout_task = None

        await self.channel_layer.group_add(
            establishment_group_name(establishment_id=self.establishment_id),
            self.channel_name,
        )
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
                build_auth_ok_payload(
                    membership_id=membership.id,
                    session_id=ticket_payload.session_id,
                )
            )
        )

    async def _close_after_access_event(self, payload: dict) -> None:
        reason = payload.get("reason")
        if reason in {"session.revoked", "establishment.switched", "membership.deactivated"}:
            self.authenticated = False
            await self.close(code=WS_CLOSE_FORBIDDEN)

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

    async def _close_auth_failed(self, *, reason: str) -> None:
        await self._close_ws_auth(reason=reason, close_code=WS_CLOSE_AUTH_FAILED)

    async def _close_ws_auth(self, *, reason: str, close_code: int) -> None:
        logger.warning(
            "realtime_ws_auth_failed",
            extra=build_ws_auth_failure_log_context(
                establishment_id=self.establishment_id,
                reason=reason,
                close_code=close_code,
            ),
        )
        await self.close(code=close_code)
