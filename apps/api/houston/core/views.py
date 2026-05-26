from http import HTTPStatus

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.establishments.access import (
    ACCESS_STATE_INACTIVE_USER,
    ACCESS_STATE_NO_MEMBERSHIPS,
    resolve_current_access_context,
)


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class HomeView(TemplateView):
    template_name = "core/home.html"


class AppHomeView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")
    template_name = "core/app_home.html"

    def get(self, request, *args, **kwargs):
        access_context = resolve_current_access_context(request)
        status_code = (
            HTTPStatus.FORBIDDEN
            if access_context.state in {ACCESS_STATE_INACTIVE_USER, ACCESS_STATE_NO_MEMBERSHIPS}
            else HTTPStatus.OK
        )
        context = self.get_context_data(access_context=access_context)
        return self.render_to_response(context, status=status_code)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(responses=HealthResponseSerializer)
    def get(self, request):
        return Response({"status": "ok"})
