from __future__ import annotations

from rest_framework import serializers


class ObservationSubmitRequestSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=10, max_length=1000)
    temporary_upload_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        max_length=3,
    )


class ObservationSubmitResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    submitted_at = serializers.DateTimeField()
    media_count = serializers.IntegerField()
    processing_status = serializers.CharField()
