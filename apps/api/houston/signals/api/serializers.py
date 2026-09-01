from __future__ import annotations

from rest_framework import serializers

from houston.action_plans.api.serializers import (
    ActionPlanBusinessUnitSerializer,
    _serialize_business_unit,
)
from houston.action_plans.models import ActionPlanExecution
from houston.establishments.business_unit_identity import (
    business_unit_public_key,
    business_unit_public_label,
)
from houston.establishments.public_serialization import (
    resolve_activity_subject_public_label,
)
from houston.observations.media_access import build_observation_media_preview_url
from houston.signals.models import Signal
from houston.signals.reporter_display import (
    created_from_observation_media_items,
    created_from_source_observation_link,
    media_count_for_signal,
    observation_media_count,
    reporter_display_name_for_signal,
)
from houston.signals.services import structured_summary_short


class PermissionHintsSerializer(serializers.Serializer):
    can_pin = serializers.BooleanField()
    can_mark_interesting = serializers.BooleanField()
    can_archive = serializers.BooleanField()
    can_cancel = serializers.BooleanField()
    can_resolve = serializers.BooleanField()
    can_create_linked_action_plan = serializers.BooleanField()
    can_qualify_routing = serializers.BooleanField()
    can_request_resolution = serializers.BooleanField()
    can_approve_resolution_request = serializers.BooleanField()
    can_reject_resolution_request = serializers.BooleanField()
    can_cancel_resolution_request = serializers.BooleanField()


class SignalResolutionRequestSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    review_route = serializers.CharField()
    requested_at = serializers.DateTimeField()
    request_comment = serializers.CharField(allow_blank=True)
    reviewed_at = serializers.DateTimeField(allow_null=True)
    review_comment = serializers.CharField(allow_blank=True)
    canceled_at = serializers.DateTimeField(allow_null=True)
    canceled_reason = serializers.CharField(allow_blank=True)
    cancel_comment = serializers.CharField(allow_blank=True)
    requested_by_membership_id = serializers.UUIDField()
    reviewed_by_membership_id = serializers.UUIDField(allow_null=True)


class SignalResolutionRequestEventSerializer(serializers.Serializer):
    request_id = serializers.UUIDField()
    event_type = serializers.ChoiceField(
        choices=["created", "approved", "rejected", "canceled"],
    )
    occurred_at = serializers.DateTimeField()
    actor_display_name = serializers.CharField(allow_null=True)


class SignalResolutionRequestCreateSerializer(serializers.Serializer):
    request_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
    )


class SignalResolutionRequestReviewSerializer(serializers.Serializer):
    review_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
    )


class SignalResolutionRequestCancelSerializer(serializers.Serializer):
    cancel_comment = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
    )


class SignalFeedItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    structured_summary_short = serializers.CharField()
    status = serializers.CharField()
    routing_status = serializers.ChoiceField(choices=["resolved", "unassigned"])
    is_pinned = serializers.BooleanField()
    affected_business_unit_id = serializers.UUIDField(allow_null=True, required=False)
    affected_business_unit_key = serializers.CharField(allow_null=True, required=False)
    affected_business_unit_label = serializers.CharField(allow_null=True, required=False)
    responsible_business_unit_id = serializers.UUIDField(allow_null=True, required=False)
    responsible_business_unit_key = serializers.CharField(allow_null=True, required=False)
    responsible_business_unit_label = serializers.CharField(allow_null=True, required=False)
    activity_subject_id = serializers.UUIDField(allow_null=True, required=False)
    activity_subject_normalized_name = serializers.CharField(allow_null=True, required=False)
    activity_subject_label = serializers.CharField(allow_null=True, required=False)
    operational_unit_key = serializers.CharField(allow_null=True)
    location_text = serializers.CharField()
    media_count = serializers.IntegerField()
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    reporter_display_name = serializers.CharField(allow_null=True, required=False)
    aggregation_count = serializers.IntegerField()
    permission_hints = PermissionHintsSerializer()
    resolution_request = SignalResolutionRequestSerializer(allow_null=True)
    establishment_id = serializers.UUIDField(required=False)
    establishment_name = serializers.CharField(required=False)


class SignalFeedResponseSerializer(serializers.Serializer):
    items = SignalFeedItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
    applied_filters = serializers.DictField()


class SourceContextSerializer(serializers.Serializer):
    submitted_at = serializers.DateTimeField(allow_null=True)
    reporter_display_name = serializers.CharField(allow_blank=True)
    media_count = serializers.IntegerField()


class SignalDetailMediaItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    preview_url = serializers.URLField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    position = serializers.IntegerField()
    observation_id = serializers.UUIDField()


class SignalLinkedActionPlanExecutionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    requires_validation = serializers.BooleanField()
    validated_at = serializers.DateTimeField(allow_null=True)
    pilot_business_unit = ActionPlanBusinessUnitSerializer()
    last_activity_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()


class SignalDetailSerializer(SignalFeedItemSerializer):
    structured_summary = serializers.CharField()
    issue_focus = serializers.CharField(allow_blank=True)
    source_context = SourceContextSerializer()
    media_items = SignalDetailMediaItemSerializer(many=True)
    linked_action_plan_executions = SignalLinkedActionPlanExecutionSerializer(many=True)
    resolution_request_events = SignalResolutionRequestEventSerializer(many=True)
    marked_interesting_by_membership_id = serializers.UUIDField(allow_null=True)
    marked_interesting_at = serializers.DateTimeField(allow_null=True)
    resolved_by_membership_id = serializers.UUIDField(allow_null=True)
    resolved_at = serializers.DateTimeField(allow_null=True)
    resolution_origin = serializers.ChoiceField(
        choices=["manual", "resolution_request", "action_plan"],
        allow_null=True,
    )
    canceled_by_membership_id = serializers.UUIDField(allow_null=True)
    canceled_at = serializers.DateTimeField(allow_null=True)
    archived_by_membership_id = serializers.UUIDField(allow_null=True)
    archived_at = serializers.DateTimeField(allow_null=True)


class SignalQualifyRoutingRequestSerializer(serializers.Serializer):
    affected_business_unit_id = serializers.UUIDField(required=False, allow_null=True)
    responsible_business_unit_id = serializers.UUIDField(required=False, allow_null=True)
    activity_subject_id = serializers.UUIDField(required=False, allow_null=True)
    operational_unit_id = serializers.UUIDField(required=False, allow_null=True)
    issue_focus = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=80,
    )
    expected_action = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=False,
        max_length=32,
    )


class SignalQualifyRoutingResponseSerializer(SignalDetailSerializer):
    qualification_outcome = serializers.ChoiceField(choices=["updated", "merged"])
    surviving_signal_id = serializers.UUIDField()
    merged_signal_id = serializers.UUIDField(allow_null=True)


def serialize_resolution_request(resolution_request) -> dict | None:
    if resolution_request is None:
        return None
    return {
        "id": resolution_request.id,
        "status": resolution_request.status,
        "review_route": resolution_request.review_route,
        "requested_at": resolution_request.requested_at,
        "request_comment": resolution_request.request_comment or "",
        "reviewed_at": resolution_request.reviewed_at,
        "review_comment": resolution_request.review_comment or "",
        "canceled_at": resolution_request.canceled_at,
        "canceled_reason": resolution_request.canceled_reason or "",
        "cancel_comment": resolution_request.cancel_comment or "",
        "requested_by_membership_id": resolution_request.requested_by_membership_id,
        "reviewed_by_membership_id": resolution_request.reviewed_by_membership_id,
    }


def _pending_resolution_request_for_serialize(signal: Signal):
    from houston.signals.permissions import get_pending_resolution_request_for_signal

    pending_list = getattr(signal, "pending_resolution_requests", None)
    if pending_list is not None:
        return pending_list[0] if pending_list else None
    return get_pending_resolution_request_for_signal(signal)


def serialize_signal_feed_item(*, signal: Signal, membership, read_only: bool = False) -> dict:
    from houston.action_plans.permissions import can_create_linked_action_plan
    from houston.signals.permissions import (
        can_approve_resolution_request,
        can_archive_signal,
        can_cancel_own_resolution_request,
        can_cancel_signal,
        can_create_resolution_request,
        can_mark_signal_interesting,
        can_pin_signal,
        can_qualify_routing,
        can_reject_resolution_request,
        can_resolve_signal,
    )

    pending = _pending_resolution_request_for_serialize(signal)
    if read_only:
        hints = _read_only_signal_permission_hints()
    else:
        hints = {
            "can_pin": can_pin_signal(membership, signal),
            "can_mark_interesting": can_mark_signal_interesting(membership, signal),
            "can_archive": can_archive_signal(membership, signal),
            "can_cancel": can_cancel_signal(membership, signal),
            "can_resolve": can_resolve_signal(membership, signal),
            "can_create_linked_action_plan": can_create_linked_action_plan(
                membership,
                signal=signal,
            ),
            "can_qualify_routing": can_qualify_routing(
                membership,
                signal,
                proposed_affected_business_unit=signal.affected_business_unit,
                proposed_responsible_business_unit=signal.responsible_business_unit,
                proposed_activity_subject=signal.activity_subject,
            ),
            "can_request_resolution": can_create_resolution_request(membership, signal),
            "can_approve_resolution_request": (
                can_approve_resolution_request(membership, pending) if pending else False
            ),
            "can_reject_resolution_request": (
                can_reject_resolution_request(membership, pending) if pending else False
            ),
            "can_cancel_resolution_request": (
                can_cancel_own_resolution_request(membership, pending) if pending else False
            ),
        }

    return {
        "id": signal.id,
        "title": signal.title,
        "structured_summary_short": structured_summary_short(signal.structured_summary),
        "status": signal.status,
        "routing_status": signal.routing_status,
        "is_pinned": signal.is_pinned,
        "affected_business_unit_id": signal.affected_business_unit_id,
        "affected_business_unit_key": (
            business_unit_public_key(business_unit=signal.affected_business_unit)
            if signal.affected_business_unit_id
            else None
        ),
        "affected_business_unit_label": (
            business_unit_public_label(business_unit=signal.affected_business_unit)
            if signal.affected_business_unit_id
            else None
        ),
        "responsible_business_unit_id": signal.responsible_business_unit_id,
        "responsible_business_unit_key": (
            business_unit_public_key(business_unit=signal.responsible_business_unit)
            if signal.responsible_business_unit_id
            else None
        ),
        "responsible_business_unit_label": (
            business_unit_public_label(business_unit=signal.responsible_business_unit)
            if signal.responsible_business_unit_id
            else None
        ),
        "activity_subject_id": signal.activity_subject_id,
        "activity_subject_normalized_name": (
            signal.activity_subject.normalized_name if signal.activity_subject_id else None
        ),
        "activity_subject_label": resolve_activity_subject_public_label(
            activity_subject=signal.activity_subject
            if signal.activity_subject_id
            else None
        ),
        "operational_unit_key": signal.operational_unit.key if signal.operational_unit else None,
        "location_text": signal.location_text,
        "media_count": media_count_for_signal(signal),
        "last_activity_at": signal.last_activity_at,
        "created_at": signal.created_at,
        "reporter_display_name": reporter_display_name_for_signal(signal),
        "aggregation_count": getattr(signal, "aggregation_count", 0) or 0,
        "resolution_request": serialize_resolution_request(pending),
        "establishment_id": signal.establishment_id,
        "establishment_name": signal.establishment.name,
        "permission_hints": hints,
    }


def _read_only_signal_permission_hints() -> dict:
    return {
        "can_pin": False,
        "can_mark_interesting": False,
        "can_archive": False,
        "can_cancel": False,
        "can_resolve": False,
        "can_create_linked_action_plan": False,
        "can_qualify_routing": False,
        "can_request_resolution": False,
        "can_approve_resolution_request": False,
        "can_reject_resolution_request": False,
        "can_cancel_resolution_request": False,
    }


def _serialize_signal_detail_media_items(*, signal: Signal, request) -> list[dict]:
    link = created_from_source_observation_link(signal)
    if link is None:
        return []

    observation_id = link.observation_id
    return [
        {
            "id": media.id,
            "preview_url": build_observation_media_preview_url(
                request=request,
                establishment_id=signal.establishment_id,
                media_id=media.id,
            ),
            "content_type": media.content_type,
            "size_bytes": media.size_bytes,
            "position": media.position,
            "observation_id": observation_id,
        }
        for media in created_from_observation_media_items(signal)
    ]


def serialize_linked_action_plan_execution_for_signal_detail(
    execution: ActionPlanExecution,
) -> dict:
    return {
        "id": execution.id,
        "title": execution.title,
        "status": execution.status,
        "requires_validation": execution.requires_validation,
        "validated_at": execution.validated_at,
        "pilot_business_unit": _serialize_business_unit(execution.pilot_business_unit),
        "last_activity_at": execution.last_activity_at,
        "created_at": execution.created_at,
    }


def serialize_signal_detail(
    *, signal: Signal, membership, request, read_only: bool = False
) -> dict:
    from houston.action_plans.selectors import linked_action_plan_executions_for_signal_detail
    from houston.signals.selectors import (
        build_resolution_request_events,
        list_resolution_requests_for_signal,
    )

    payload = serialize_signal_feed_item(
        signal=signal,
        membership=membership,
        read_only=read_only,
    )
    # Detail keeps resolution_request as pending-only for actions; history is projected.
    requests = list_resolution_requests_for_signal(signal_id=signal.id)
    payload["resolution_request_events"] = build_resolution_request_events(requests)
    payload["structured_summary"] = signal.structured_summary
    payload["issue_focus"] = signal.issue_focus or ""
    payload["marked_interesting_by_membership_id"] = (
        signal.marked_interesting_by_membership_id
    )
    payload["marked_interesting_at"] = signal.marked_interesting_at
    payload["resolved_by_membership_id"] = signal.resolved_by_membership_id
    payload["resolved_at"] = signal.resolved_at
    payload["resolution_origin"] = signal.resolution_origin
    payload["canceled_by_membership_id"] = signal.canceled_by_membership_id
    payload["canceled_at"] = signal.canceled_at
    payload["archived_by_membership_id"] = signal.archived_by_membership_id
    payload["archived_at"] = signal.archived_at

    link = created_from_source_observation_link(signal)
    if link is None:
        payload["source_context"] = {
            "submitted_at": None,
            "reporter_display_name": "",
            "media_count": 0,
        }
        payload["media_items"] = []
    else:
        from houston.accounts.display import user_display_name

        observation = link.observation
        display = user_display_name(observation.submitted_by_membership.user)
        payload["source_context"] = {
            "submitted_at": observation.submitted_at,
            "reporter_display_name": display,
            "media_count": observation_media_count(observation),
        }
        payload["media_items"] = _serialize_signal_detail_media_items(
            signal=signal,
            request=request,
        )
    payload["linked_action_plan_executions"] = [
        serialize_linked_action_plan_execution_for_signal_detail(execution)
        for execution in linked_action_plan_executions_for_signal_detail(
            membership=membership,
            signal=signal,
        )
    ]
    return payload
