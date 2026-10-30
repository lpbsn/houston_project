from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from houston.accounts.authentication import BearerAccessTokenAuthentication
from houston.action_plans.day_selectors import my_day_tasks
from houston.establishments.permissions import HasActiveMembership
from houston.uploads.access import resolve_observation_actor_membership
from houston.uploads.api.views import EstablishmentScopedObservationMixin


class MyDayTaskSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    execution_id = serializers.UUIDField()
    execution_title = serializers.CharField()
    pole = serializers.CharField()
    due_at = serializers.DateTimeField(allow_null=True)
    all_day = serializers.BooleanField()
    shared = serializers.BooleanField()
    bucket = serializers.ChoiceField(choices=["overdue", "today", "upcoming", "undated"])


class MyDayResponseSerializer(serializers.Serializer):
    items = MyDayTaskSerializer(many=True)
    next_offset = serializers.IntegerField(allow_null=True)
    timezone = serializers.CharField()


class MyDayView(EstablishmentScopedObservationMixin, APIView):
    authentication_classes = [BearerAccessTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated, HasActiveMembership]

    @extend_schema(
        tags=["action-plans"],
        parameters=[OpenApiParameter(name="offset", type=int)],
        responses={200: MyDayResponseSerializer},
    )
    def get(self, request, establishment_id):
        membership = resolve_observation_actor_membership(
            request,
            establishment_id=self.establishment_id,
        )
        if membership is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            offset = int(request.query_params.get("offset", "0"))
            if offset < 0:
                raise ValueError
        except (ValueError, TypeError):
            return Response({"detail": "Invalid offset."}, status=status.HTTP_400_BAD_REQUEST)
        # No full-history load or per-plan requests. Stable ordering, 30 rows per page.
        rows = list(my_day_tasks(membership=membership)[offset : offset + 31])
        buckets = ("overdue", "today", "upcoming", "undated")
        items = [
            {
                "id": row.id,
                "title": row.task,
                "execution_id": row.action_plan_execution_id,
                "execution_title": row.action_plan_execution.title,
                "pole": row.execution_team.business_unit.specific_name,
                "due_at": row.due_at,
                "all_day": row.deadline_at is None and row.action_plan_execution.all_day,
                "shared": row.assigned_membership_id is None,
                "bucket": buckets[row.day_bucket],
            }
            for row in rows[:30]
        ]
        return Response(
            MyDayResponseSerializer(
                {
                    "items": items,
                    "next_offset": offset + 30 if len(rows) > 30 else None,
                    "timezone": membership.establishment.timezone,
                }
            ).data
        )
