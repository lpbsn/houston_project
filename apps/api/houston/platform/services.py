from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TypeVar
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.accounts.models import User
from houston.platform.exceptions import PlatformLifecycleDenied, PlatformLifecycleFailed
from houston.platform.models import PlatformLifecycleEvent, PlatformOperatorAccess

logger = logging.getLogger(__name__)

T = TypeVar("T")


def resolve_user_by_identifier(identifier: str) -> User | None:
    normalized = identifier.strip()
    if not normalized:
        return None
    if "@" in normalized:
        email = User.normalize_email_value(normalized)
        if email is None:
            return None
        return User.objects.filter(email__iexact=email).first()
    return User.objects.filter(username=normalized).first()


def grant_platform_operator(*, user: User) -> PlatformOperatorAccess:
    now = timezone.now()
    access, created = PlatformOperatorAccess.objects.get_or_create(
        user=user,
        defaults={
            "is_active": True,
            "granted_at": now,
            "revoked_at": None,
        },
    )
    if created:
        return access
    if access.is_active:
        return access
    access.is_active = True
    access.granted_at = now
    access.revoked_at = None
    access.save(update_fields=["is_active", "granted_at", "revoked_at", "updated_at"])
    return access


def revoke_platform_operator(*, user: User) -> PlatformOperatorAccess | None:
    try:
        access = PlatformOperatorAccess.objects.get(user=user)
    except PlatformOperatorAccess.DoesNotExist:
        return None
    if not access.is_active:
        return access
    access.is_active = False
    access.revoked_at = timezone.now()
    access.save(update_fields=["is_active", "revoked_at", "updated_at"])
    return access


def record_lifecycle_event(
    *,
    operator: User,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    result: str,
    justification: str = "",
    error_code: str = "",
) -> PlatformLifecycleEvent:
    event = PlatformLifecycleEvent.objects.create(
        operator=operator,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        justification=justification,
        result=result,
        error_code=error_code,
    )
    logger.info(
        "platform_lifecycle_event",
        extra={
            "action": action,
            "resource_type": resource_type,
            "resource_id": None if resource_id is None else str(resource_id),
            "result": result,
            "error_code": error_code or None,
            "operator_id": str(operator.pk),
        },
    )
    return event


def execute_platform_lifecycle(
    *,
    operator: User,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    mutate: Callable[[], T],
    justification: str = "",
) -> T:
    try:
        with transaction.atomic():
            result = mutate()
            record_lifecycle_event(
                operator=operator,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                result=PlatformLifecycleEvent.Result.OK,
                justification=justification,
            )
            return result
    except PlatformLifecycleDenied as exc:
        record_lifecycle_event(
            operator=operator,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=PlatformLifecycleEvent.Result.DENIED,
            justification=justification,
            error_code=exc.code,
        )
        raise
    except PlatformLifecycleFailed as exc:
        record_lifecycle_event(
            operator=operator,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=PlatformLifecycleEvent.Result.FAILED,
            justification=justification,
            error_code=exc.code,
        )
        raise
    except IntegrityError:
        record_lifecycle_event(
            operator=operator,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=PlatformLifecycleEvent.Result.FAILED,
            justification=justification,
            error_code="integrity_error",
        )
        raise
    except Exception:
        record_lifecycle_event(
            operator=operator,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=PlatformLifecycleEvent.Result.FAILED,
            justification=justification,
            error_code="unexpected_error",
        )
        raise
