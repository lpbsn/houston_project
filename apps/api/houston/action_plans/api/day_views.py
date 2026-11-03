from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers, status
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.action_plans.day_selectors import (
    MY_DAY_SECTIONS,
    MyDayCursorError,
    my_day_auth_context_hash,
    parse_my_day_cursor,
    read_my_day,
)
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


class MyDayTaskSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    due_at = serializers.DateTimeField(allow_null=True)
    late = serializers.BooleanField()
    shared = serializers.BooleanField()
    pole = serializers.CharField(allow_null=True)


class MyDayCardSerializer(serializers.Serializer):
    execution_id = serializers.UUIDField()
    title = serializers.CharField()
    pilot_pole = serializers.CharField()
    section = serializers.ChoiceField(choices=list(MY_DAY_SECTIONS))
    kind = serializers.ChoiceField(
        choices=[
            "validate",
            "awaiting_validation",
            "scheduled",
            "realize",
            "tasks",
            "follow",
            "finalize",
            "relay",
        ]
    )
    start_at = serializers.DateTimeField(allow_null=True)
    plan_end_at = serializers.DateTimeField(allow_null=True)
    plan_all_day = serializers.BooleanField()
    late = serializers.BooleanField()
    own_tasks_done = serializers.BooleanField()
    tasks = MyDayTaskSerializer(many=True)


class MyDaySectionSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    next_cursor = serializers.CharField(allow_null=True)
    items = MyDayCardSerializer(many=True)


class MyDaySectionsSerializer(serializers.Serializer):
    action = MyDaySectionSerializer()
    follow = MyDaySectionSerializer()
    upcoming = MyDaySectionSerializer()


class MyDayResponseSerializer(serializers.Serializer):
    timezone = serializers.CharField()
    sections = MyDaySectionsSerializer(allow_null=True)
    section = serializers.ChoiceField(choices=list(MY_DAY_SECTIONS), allow_null=True)
    next_cursor = serializers.CharField(allow_null=True)
    items = MyDayCardSerializer(many=True, allow_null=True)


def _card_payload(card) -> dict:
    return {
        "execution_id": card.execution_id,
        "title": card.title,
        "pilot_pole": card.pilot_pole,
        "section": card.section,
        "kind": card.kind,
        "start_at": card.start_at,
        "plan_end_at": card.plan_end_at,
        "plan_all_day": card.plan_all_day,
        "late": card.late,
        "own_tasks_done": card.own_tasks_done,
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "due_at": task.due_at,
                "late": task.late,
                "shared": task.shared,
                "pole": task.pole,
            }
            for task in card.tasks
        ],
    }


def _section_payload(page) -> dict:
    return {
        "count": page.count,
        "next_cursor": page.next_cursor,
        "items": [_card_payload(card) for card in page.items],
    }


class MyDayView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        parameters=[
            OpenApiParameter(name="section", type=str, required=False),
            OpenApiParameter(name="cursor", type=str, required=False),
        ],
        responses={200: MyDayResponseSerializer},
    )
    def get(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        # Warm the establishment so the selector does not query it again.
        _ = membership.establishment.timezone
        scope_ids = list(membership.scope_links.values_list("business_unit_id", flat=True))
        auth_hash = my_day_auth_context_hash(membership=membership, scope_ids=scope_ids)
        section = request.query_params.get("section")
        raw_cursor = request.query_params.get("cursor")
        if (section is None) != (raw_cursor is None):
            return Response({"detail": "Invalid cursor."}, status=status.HTTP_400_BAD_REQUEST)
        if section is not None and section not in MY_DAY_SECTIONS:
            return Response({"detail": "Invalid cursor."}, status=status.HTTP_400_BAD_REQUEST)
        cursor = None
        if raw_cursor is not None:
            try:
                cursor = parse_my_day_cursor(raw_cursor, now=timezone.now(), auth_hash=auth_hash)
            except MyDayCursorError:
                return Response({"detail": "Invalid cursor."}, status=status.HTTP_400_BAD_REQUEST)
            if cursor.section != section:
                return Response({"detail": "Invalid cursor."}, status=status.HTTP_400_BAD_REQUEST)
        reading = read_my_day(
            membership=membership,
            scope_ids=scope_ids,
            auth_hash=auth_hash,
            cursor=cursor,
        )
        if cursor is None:
            payload = {
                "timezone": membership.establishment.timezone,
                "sections": {
                    name: _section_payload(reading.sections[name]) for name in MY_DAY_SECTIONS
                },
                "section": None,
                "next_cursor": None,
                "items": None,
            }
        else:
            payload = {
                "timezone": membership.establishment.timezone,
                "sections": None,
                "section": reading.section,
                "next_cursor": reading.next_cursor,
                "items": [_card_payload(card) for card in reading.items],
            }
        return Response(MyDayResponseSerializer(payload).data)
