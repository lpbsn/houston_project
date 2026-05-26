from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class HomeView(TemplateView):
    template_name = "core/home.html"


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses=HealthResponseSerializer)
    def get(self, request):
        return Response({"status": "ok"})
