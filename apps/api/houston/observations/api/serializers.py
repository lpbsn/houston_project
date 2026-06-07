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


class ObservationProcessingSignalSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    affected_business_unit_key = serializers.CharField(allow_blank=True)
    affected_business_unit_label = serializers.CharField(allow_blank=True)
    responsible_business_unit_key = serializers.CharField(allow_blank=True)
    responsible_business_unit_label = serializers.CharField(allow_blank=True)
    activity_subject_key = serializers.CharField(allow_blank=True)
    activity_subject_label = serializers.CharField(allow_blank=True)
    location_text = serializers.CharField(allow_blank=True)


class ObservationProcessingStatusResponseSerializer(serializers.Serializer):
    observation_id = serializers.UUIDField()
    status = serializers.CharField()
    outcome = serializers.CharField(allow_blank=True)
    signal_ids = serializers.ListField(child=serializers.UUIDField())
    signals = ObservationProcessingSignalSummarySerializer(many=True)
    last_error_code = serializers.CharField(allow_blank=True)
    ux_status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    processed_at = serializers.DateTimeField(allow_null=True)
