from __future__ import annotations

from rest_framework import serializers


class GamificationPeriodSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()


class GamificationCurrentSummarySerializer(serializers.Serializer):
    season_id = serializers.UUIDField(allow_null=True)
    period = GamificationPeriodSerializer()
    score = serializers.IntegerField()
    grade = serializers.CharField(allow_null=True)
    next_grade = serializers.CharField(allow_null=True)
    next_grade_threshold = serializers.IntegerField(allow_null=True)
    points_to_next_grade = serializers.IntegerField()
    progress_ratio = serializers.FloatField()
    is_max_grade = serializers.BooleanField()


class GamificationGradeRuleSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    threshold = serializers.IntegerField()


class GamificationPointsRuleSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    points = serializers.IntegerField(allow_null=True)
    points_min = serializers.IntegerField()
    points_max = serializers.IntegerField()


class GamificationRulesSerializer(serializers.Serializer):
    grades = GamificationGradeRuleSerializer(many=True)
    points = GamificationPointsRuleSerializer(many=True)


class GamificationSeasonItemSerializer(serializers.Serializer):
    season_id = serializers.UUIDField(allow_null=True)
    period = GamificationPeriodSerializer()
    status = serializers.CharField()
    score = serializers.IntegerField()
    grade = serializers.CharField(allow_null=True)
    closed_at = serializers.DateTimeField(allow_null=True)


class GamificationSeasonListSerializer(serializers.Serializer):
    items = GamificationSeasonItemSerializer(many=True)


class GamificationOverviewSerializer(serializers.Serializer):
    current = GamificationCurrentSummarySerializer()
    rules = GamificationRulesSerializer()
    seasons = GamificationSeasonListSerializer()


class GamificationTransactionSeasonSerializer(serializers.Serializer):
    season_id = serializers.UUIDField()
    period = GamificationPeriodSerializer()
    status = serializers.CharField()


class GamificationTransactionSourceSerializer(serializers.Serializer):
    type = serializers.CharField()
    id = serializers.CharField()


class GamificationTransactionItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    occurred_at = serializers.DateTimeField()
    delta = serializers.IntegerField()
    reason_code = serializers.CharField()
    reason_label = serializers.CharField()
    season = GamificationTransactionSeasonSerializer()
    source = GamificationTransactionSourceSerializer(allow_null=True)
    is_correction = serializers.BooleanField()
    is_reversal = serializers.BooleanField()
    reversed_transaction_id = serializers.UUIDField(allow_null=True)


class GamificationTransactionListSerializer(serializers.Serializer):
    items = GamificationTransactionItemSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
