from __future__ import annotations

from rest_framework import serializers


class TemporaryUploadResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    expires_at = serializers.DateTimeField()


class TranscriptionResponseSerializer(serializers.Serializer):
    text = serializers.CharField()
    language = serializers.CharField(allow_blank=True)
    correlation_id = serializers.UUIDField()
