from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.signals.constants import (
    SIGNAL_RESOLUTION_BLOCKING_EXECUTION_DETAIL,
    SIGNAL_RESOLUTION_NO_DIRECTOR_REVIEWER_DETAIL,
    SIGNAL_RESOLUTION_NO_MANAGER_REVIEWER_DETAIL,
    SIGNAL_RESOLUTION_NO_RESPONSIBLE_POLE_DETAIL,
    SIGNAL_RESOLUTION_NOT_OPEN_DETAIL,
    SIGNAL_RESOLUTION_NOT_PENDING_DETAIL,
    SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
    SIGNAL_RESOLUTION_PENDING_EXISTS_DETAIL,
    SIGNAL_RESOLUTION_REQUEST_COMMENT_MAX_LENGTH,
    SIGNAL_RESOLUTION_REQUESTER_ENGAGED_DETAIL,
    SIGNAL_RESOLUTION_REVIEWER_INELIGIBLE_DETAIL,
)
from houston.signals.exceptions import (
    SignalPermissionError,
    SignalStateError,
    SignalValidationError,
)
from houston.signals.models import Signal, SignalResolutionRequest
from houston.signals.permissions import (
    _signal_has_blocking_linked_executions,
    can_cancel_own_resolution_request,
    can_review_resolution_request,
    is_eligible_resolution_reviewer,
    list_eligible_resolution_reviewers_for_route,
    resolve_review_route_for_membership,
)
from houston.signals.services import (
    _lock_signal_created_from_set_or_self,
    _resolve_signal_after_lock,
    _schedule_signal_invalidation,
)


def _normalize_optional_comment(comment: str | None) -> str:
    normalized = (comment or "").strip()
    if len(normalized) > SIGNAL_RESOLUTION_REQUEST_COMMENT_MAX_LENGTH:
        raise SignalValidationError("Comment is too long.")
    return normalized


def cancel_pending_resolution_request_for_signal(
    *,
    signal: Signal,
    reason: str,
    notify_requester: bool = True,
) -> SignalResolutionRequest | None:
    """Idempotent auto-cancel of the pending request for a signal (caller holds signal lock)."""
    pending = (
        SignalResolutionRequest.objects.select_for_update()
        .filter(
            signal_id=signal.id,
            status=SignalResolutionRequest.Status.PENDING,
        )
        .first()
    )
    if pending is None:
        return None

    now = timezone.now()
    pending.status = SignalResolutionRequest.Status.CANCELED
    pending.canceled_at = now
    pending.canceled_reason = reason
    pending.save(
        update_fields=["status", "canceled_at", "canceled_reason", "updated_at"],
    )

    if notify_requester:
        from houston.notifications.scheduling import (
            schedule_signal_resolution_request_auto_canceled_notification,
        )

        schedule_signal_resolution_request_auto_canceled_notification(
            resolution_request_id=pending.id,
        )
    return pending


def get_pending_resolution_request_locked(*, signal_id) -> SignalResolutionRequest | None:
    return (
        SignalResolutionRequest.objects.select_for_update()
        .filter(
            signal_id=signal_id,
            status=SignalResolutionRequest.Status.PENDING,
        )
        .select_related("requested_by_membership")
        .first()
    )


@transaction.atomic
def create_signal_resolution_request(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership,
    request_comment: str | None = None,
) -> SignalResolutionRequest:
    locked_self, _, _ = _lock_signal_created_from_set_or_self(signal=signal)

    if locked_self.status != Signal.Status.OPEN:
        raise SignalStateError(SIGNAL_RESOLUTION_NOT_OPEN_DETAIL)
    if locked_self.responsible_business_unit_id is None:
        raise SignalValidationError(SIGNAL_RESOLUTION_NO_RESPONSIBLE_POLE_DETAIL)

    review_route = resolve_review_route_for_membership(actor_membership)
    if review_route is None:
        raise SignalPermissionError("Permission denied.")

    from houston.establishments.membership_scope import membership_scope_covers_business_unit
    from houston.signals.permissions import can_view_signal_detail

    if actor_membership.status != EstablishmentMembership.Status.ACTIVE:
        raise SignalPermissionError("Permission denied.")
    if locked_self.establishment_id != actor_membership.establishment_id:
        raise SignalPermissionError("Permission denied.")
    if not can_view_signal_detail(actor_membership, locked_self):
        raise SignalPermissionError("Permission denied.")

    if review_route == SignalResolutionRequest.ReviewRoute.STAFF_TO_MANAGER:
        if actor_membership.role != EstablishmentMembership.Role.STAFF:
            raise SignalPermissionError("Permission denied.")
    elif review_route == SignalResolutionRequest.ReviewRoute.MANAGER_TO_DIRECTOR:
        if actor_membership.role != EstablishmentMembership.Role.MANAGER:
            raise SignalPermissionError("Permission denied.")
        if not membership_scope_covers_business_unit(
            actor_membership,
            locked_self.responsible_business_unit,
        ):
            raise SignalPermissionError("Permission denied.")
    else:
        raise SignalPermissionError("Permission denied.")

    if get_pending_resolution_request_locked(signal_id=locked_self.id) is not None:
        raise SignalStateError(SIGNAL_RESOLUTION_PENDING_EXISTS_DETAIL)
    if _signal_has_blocking_linked_executions(locked_self):
        raise SignalStateError(SIGNAL_RESOLUTION_BLOCKING_EXECUTION_DETAIL)

    reviewers = list_eligible_resolution_reviewers_for_route(
        signal=locked_self,
        review_route=review_route,
    )
    if not reviewers:
        if review_route == SignalResolutionRequest.ReviewRoute.STAFF_TO_MANAGER:
            raise SignalValidationError(SIGNAL_RESOLUTION_NO_MANAGER_REVIEWER_DETAIL)
        raise SignalValidationError(SIGNAL_RESOLUTION_NO_DIRECTOR_REVIEWER_DETAIL)

    comment = _normalize_optional_comment(request_comment)
    now = timezone.now()
    try:
        resolution_request = SignalResolutionRequest.objects.create(
            signal=locked_self,
            requested_by_membership=actor_membership,
            requested_at=now,
            review_route=review_route,
            status=SignalResolutionRequest.Status.PENDING,
            request_comment=comment,
        )
    except IntegrityError as exc:
        raise SignalStateError(SIGNAL_RESOLUTION_PENDING_EXISTS_DETAIL) from exc

    _schedule_signal_invalidation(signal=locked_self, reason="signal.updated")
    from houston.notifications.scheduling import (
        schedule_signal_resolution_request_created_notification,
    )

    schedule_signal_resolution_request_created_notification(
        resolution_request_id=resolution_request.id,
        actor_membership_id=actor_membership.id,
    )
    return resolution_request


@transaction.atomic
def approve_signal_resolution_request(
    *,
    resolution_request: SignalResolutionRequest,
    actor_membership: EstablishmentMembership,
    review_comment: str | None = None,
) -> SignalResolutionRequest:
    locked_self, _, _ = _lock_signal_created_from_set_or_self(
        signal=resolution_request.signal,
    )
    locked_request = (
        SignalResolutionRequest.objects.select_for_update()
        .select_related("signal", "requested_by_membership")
        .get(pk=resolution_request.pk)
    )

    if locked_request.status != SignalResolutionRequest.Status.PENDING:
        raise SignalStateError(SIGNAL_RESOLUTION_NOT_PENDING_DETAIL)
    if locked_self.status != Signal.Status.OPEN:
        raise SignalStateError(SIGNAL_RESOLUTION_NOT_OPEN_DETAIL)
    if _signal_has_blocking_linked_executions(locked_self):
        raise SignalStateError(SIGNAL_RESOLUTION_BLOCKING_EXECUTION_DETAIL)
    if not is_eligible_resolution_reviewer(
        actor_membership,
        signal=locked_self,
        review_route=locked_request.review_route,
    ):
        raise SignalPermissionError(SIGNAL_RESOLUTION_REVIEWER_INELIGIBLE_DETAIL)

    comment = _normalize_optional_comment(review_comment)
    now = timezone.now()
    locked_request.status = SignalResolutionRequest.Status.APPROVED
    locked_request.reviewed_by_membership = actor_membership
    locked_request.reviewed_at = now
    locked_request.review_comment = comment
    locked_request.save(
        update_fields=[
            "status",
            "reviewed_by_membership",
            "reviewed_at",
            "review_comment",
            "updated_at",
        ],
    )

    _resolve_signal_after_lock(
        original_signal=locked_self,
        locked_self=locked_self,
        actor_membership=actor_membership,
        resolution_origin=SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
    )
    _schedule_signal_invalidation(signal=locked_self, reason="signal.updated")

    from houston.notifications.scheduling import (
        schedule_signal_resolution_request_reviewed_notification,
    )

    schedule_signal_resolution_request_reviewed_notification(
        resolution_request_id=locked_request.id,
        actor_membership_id=actor_membership.id,
    )
    return locked_request


@transaction.atomic
def reject_signal_resolution_request(
    *,
    resolution_request: SignalResolutionRequest,
    actor_membership: EstablishmentMembership,
    review_comment: str | None = None,
) -> SignalResolutionRequest:
    locked_self, _, _ = _lock_signal_created_from_set_or_self(
        signal=resolution_request.signal,
    )
    locked_request = (
        SignalResolutionRequest.objects.select_for_update()
        .select_related("signal")
        .get(pk=resolution_request.pk)
    )

    if locked_request.status != SignalResolutionRequest.Status.PENDING:
        raise SignalStateError(SIGNAL_RESOLUTION_NOT_PENDING_DETAIL)
    if not can_review_resolution_request(actor_membership, locked_request):
        # Re-check eligibility against locked signal state.
        if not is_eligible_resolution_reviewer(
            actor_membership,
            signal=locked_self,
            review_route=locked_request.review_route,
        ):
            raise SignalPermissionError(SIGNAL_RESOLUTION_REVIEWER_INELIGIBLE_DETAIL)
        raise SignalPermissionError("Permission denied.")

    if not is_eligible_resolution_reviewer(
        actor_membership,
        signal=locked_self,
        review_route=locked_request.review_route,
    ):
        raise SignalPermissionError(SIGNAL_RESOLUTION_REVIEWER_INELIGIBLE_DETAIL)

    comment = _normalize_optional_comment(review_comment)
    now = timezone.now()
    locked_request.status = SignalResolutionRequest.Status.REJECTED
    locked_request.reviewed_by_membership = actor_membership
    locked_request.reviewed_at = now
    locked_request.review_comment = comment
    locked_request.save(
        update_fields=[
            "status",
            "reviewed_by_membership",
            "reviewed_at",
            "review_comment",
            "updated_at",
        ],
    )
    _schedule_signal_invalidation(signal=locked_self, reason="signal.updated")

    from houston.notifications.scheduling import (
        schedule_signal_resolution_request_reviewed_notification,
    )

    schedule_signal_resolution_request_reviewed_notification(
        resolution_request_id=locked_request.id,
        actor_membership_id=actor_membership.id,
    )
    return locked_request


@transaction.atomic
def cancel_signal_resolution_request_by_requester(
    *,
    resolution_request: SignalResolutionRequest,
    actor_membership: EstablishmentMembership,
    cancel_comment: str | None = None,
) -> SignalResolutionRequest:
    locked_self, _, _ = _lock_signal_created_from_set_or_self(
        signal=resolution_request.signal,
    )
    locked_request = (
        SignalResolutionRequest.objects.select_for_update()
        .select_related("signal")
        .get(pk=resolution_request.pk)
    )

    if locked_request.status != SignalResolutionRequest.Status.PENDING:
        raise SignalStateError(SIGNAL_RESOLUTION_NOT_PENDING_DETAIL)
    if not can_cancel_own_resolution_request(actor_membership, locked_request):
        raise SignalPermissionError("Permission denied.")

    comment = _normalize_optional_comment(cancel_comment)
    now = timezone.now()
    locked_request.status = SignalResolutionRequest.Status.CANCELED
    locked_request.canceled_at = now
    locked_request.canceled_reason = (
        SignalResolutionRequest.CanceledReason.CANCELED_BY_REQUESTER
    )
    locked_request.cancel_comment = comment
    locked_request.save(
        update_fields=[
            "status",
            "canceled_at",
            "canceled_reason",
            "cancel_comment",
            "updated_at",
        ],
    )
    _schedule_signal_invalidation(signal=locked_self, reason="signal.updated")
    return locked_request


def enforce_requester_engagement_or_cancel_pending_on_resolve(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership | None,
) -> None:
    """Call after signal row lock, before resolving.

    - Requester with pending request: refuse (engagement).
    - Other actor / system resolve: cancel pending as resolved elsewhere.
    """
    pending = get_pending_resolution_request_locked(signal_id=signal.id)
    if pending is None:
        return

    if (
        actor_membership is not None
        and pending.requested_by_membership_id == actor_membership.id
    ):
        raise SignalStateError(SIGNAL_RESOLUTION_REQUESTER_ENGAGED_DETAIL)

    cancel_pending_resolution_request_for_signal(
        signal=signal,
        reason=SignalResolutionRequest.CanceledReason.SIGNAL_RESOLVED_ELSEWHERE,
        notify_requester=True,
    )
