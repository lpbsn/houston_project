from __future__ import annotations

from rest_framework import serializers

from houston.establishments.models import ContentReport
from houston.establishments.safety_constants import CONTENT_REPORT_REASON_MAX_LENGTH


class MembershipBlockResponseSerializer(serializers.Serializer):
    blocker_membership_id = serializers.UUIDField()
    blocked_membership_id = serializers.UUIDField()


class ContentReportCreateRequestSerializer(serializers.Serializer):
    content_kind = serializers.ChoiceField(choices=ContentReport.ContentKind.choices)
    reason = serializers.CharField(max_length=CONTENT_REPORT_REASON_MAX_LENGTH)
    target_membership_id = serializers.UUIDField(required=False)
    content_id = serializers.UUIDField(required=False)


class ContentReportResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    content_kind = serializers.CharField()
