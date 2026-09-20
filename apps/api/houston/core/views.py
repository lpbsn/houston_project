from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class ClientRequirementsResponseSerializer(serializers.Serializer):
    android_min_supported_version_code = serializers.IntegerField(min_value=0)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=HealthResponseSerializer)
    def get(self, request):
        return Response({"status": "ok"})


class ClientRequirementsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        responses=ClientRequirementsResponseSerializer,
        description=(
            "Public client policy for native store builds. "
            "Default min Android versionCode is 0 (no forced update)."
        ),
    )
    def get(self, request):
        return Response(
            {
                "android_min_supported_version_code": (
                    settings.HOUSTON_ANDROID_MIN_SUPPORTED_VERSION_CODE
                ),
            }
        )
