from __future__ import annotations

from rest_framework import serializers


class AnalyticsPeriodSerializer(serializers.Serializer):
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()


class AnalyticsRecurrenceWindowSerializer(serializers.Serializer):
    window_start = serializers.DateTimeField()
    window_end = serializers.DateTimeField()


class AnalyticsMetricComparisonSerializer(serializers.Serializer):
    current_value = serializers.FloatField(allow_null=True)
    previous_value = serializers.FloatField(allow_null=True)
    absolute_delta = serializers.FloatField(allow_null=True)
    relative_change = serializers.FloatField(allow_null=True)
    relative_change_status = serializers.CharField()


class AnalyticsBusinessAssignmentCoverageSerializer(serializers.Serializer):
    total_count = serializers.IntegerField()
    with_pattern_count = serializers.IntegerField()
    without_pattern_count = serializers.IntegerField()
    coverage_rate = serializers.FloatField(allow_null=True)


class AnalyticsTechnicalClassificationStateSerializer(serializers.Serializer):
    total_count = serializers.IntegerField()
    technical_state_breakdown = serializers.DictField(child=serializers.IntegerField())
    technical_terminal_success_count = serializers.IntegerField()
    technical_pending_or_error_count = serializers.IntegerField()


class AnalyticsKPIResultSerializer(serializers.Serializer):
    analytics_signal_population_count = serializers.IntegerField()
    signals_analyzed_count = serializers.IntegerField()
    operational_patterns_count = serializers.IntegerField()
    actionable_signals_count = serializers.IntegerField()
    median_resolution_seconds = serializers.FloatField(allow_null=True)
    resolution_time_signal_count = serializers.IntegerField()
    invalid_resolution_duration_count = serializers.IntegerField()
    business_assignment_coverage = AnalyticsBusinessAssignmentCoverageSerializer()
    technical_classification_state = AnalyticsTechnicalClassificationStateSerializer()
    recurring_patterns_count = serializers.IntegerField()
    recurrence_window = AnalyticsRecurrenceWindowSerializer()
    recurrence_status = serializers.CharField()


class AnalyticsDashboardResponseSerializer(serializers.Serializer):
    current_period = AnalyticsPeriodSerializer()
    previous_period = AnalyticsPeriodSerializer()
    current_kpis = AnalyticsKPIResultSerializer()
    previous_kpis = AnalyticsKPIResultSerializer()
    signals_analyzed_count = AnalyticsMetricComparisonSerializer()
    operational_patterns_count = AnalyticsMetricComparisonSerializer()
    actionable_signals_count = AnalyticsMetricComparisonSerializer()
    median_resolution_seconds = AnalyticsMetricComparisonSerializer()
    recurring_patterns_count = AnalyticsMetricComparisonSerializer()
    recurrence_status = serializers.CharField()


class AnalyticsPatternEstablishmentSummarySerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    name = serializers.CharField()
    signal_count = serializers.IntegerField()


class AnalyticsPatternListItemSerializer(serializers.Serializer):
    pattern_id = serializers.UUIDField()
    label = serializers.CharField()
    normalized_label = serializers.CharField()
    status = serializers.CharField()
    signal_count = serializers.IntegerField()
    previous_signal_count = serializers.IntegerField()
    signal_count_comparison = AnalyticsMetricComparisonSerializer()
    last_seen_at = serializers.DateTimeField()
    actionable_signal_count = serializers.IntegerField()
    establishment_count = serializers.IntegerField()
    establishments = AnalyticsPatternEstablishmentSummarySerializer(many=True)
    is_recurrent = serializers.BooleanField()
    occurrence_count_30d = serializers.IntegerField()
    distinct_day_count_30d = serializers.IntegerField()
    recurrence_window = AnalyticsRecurrenceWindowSerializer()
    recurrence_status = serializers.CharField()


class AnalyticsPatternListResponseSerializer(serializers.Serializer):
    current_period = AnalyticsPeriodSerializer()
    previous_period = AnalyticsPeriodSerializer()
    items = AnalyticsPatternListItemSerializer(many=True)
    total_count = serializers.IntegerField()
    page_size = serializers.IntegerField()
    has_more = serializers.BooleanField()
    next_cursor = serializers.CharField(allow_null=True)
    recurrence_window = AnalyticsRecurrenceWindowSerializer()
    recurrence_status = serializers.CharField()


class AnalyticsPatternFilterEstablishmentOptionSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    name = serializers.CharField()


class AnalyticsPatternFilterBusinessUnitOptionSerializer(serializers.Serializer):
    business_unit_id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    establishment_id = serializers.UUIDField(allow_null=True)
    is_unassigned = serializers.BooleanField()


class AnalyticsPatternFilterOptionsResponseSerializer(serializers.Serializer):
    establishments = AnalyticsPatternFilterEstablishmentOptionSerializer(many=True)
    responsible_business_units = AnalyticsPatternFilterBusinessUnitOptionSerializer(many=True)
    includes_unassigned = serializers.BooleanField()


class AnalyticsPatternIdentitySerializer(serializers.Serializer):
    pattern_id = serializers.UUIDField()
    label = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    merged_into_pattern_id = serializers.UUIDField(allow_null=True)


class AnalyticsPatternDetailMetricsSerializer(serializers.Serializer):
    signal_count = serializers.IntegerField()
    previous_signal_count = serializers.IntegerField()
    signal_count_comparison = AnalyticsMetricComparisonSerializer()
    actionable_signal_count = serializers.IntegerField()
    last_seen_at = serializers.DateTimeField()
    establishment_count = serializers.IntegerField()


class AnalyticsPatternTrendBucketSerializer(serializers.Serializer):
    bucket_date = serializers.DateField()
    bucket_start = serializers.DateTimeField()
    bucket_end = serializers.DateTimeField()
    signal_count = serializers.IntegerField()


class AnalyticsPatternStatusDistributionBucketSerializer(serializers.Serializer):
    status = serializers.CharField()
    signal_count = serializers.IntegerField()


class AnalyticsPatternEstablishmentDistributionBucketSerializer(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    name = serializers.CharField()
    signal_count = serializers.IntegerField()


class AnalyticsPatternBusinessUnitDistributionBucketSerializer(serializers.Serializer):
    business_unit_id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    signal_count = serializers.IntegerField()


class AnalyticsPatternDrilldownContextSerializer(serializers.Serializer):
    pattern_id = serializers.UUIDField()
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    organization_id = serializers.UUIDField(allow_null=True)
    establishment_id = serializers.UUIDField(allow_null=True)


class AnalyticsPatternDetailResponseSerializer(serializers.Serializer):
    identity = AnalyticsPatternIdentitySerializer()
    current_period = AnalyticsPeriodSerializer()
    previous_period = AnalyticsPeriodSerializer()
    metrics = AnalyticsPatternDetailMetricsSerializer()
    is_recurrent = serializers.BooleanField()
    occurrence_count_30d = serializers.IntegerField()
    distinct_day_count_30d = serializers.IntegerField()
    recurrence_window = AnalyticsRecurrenceWindowSerializer()
    recurrence_status = serializers.CharField()
    trend_timezone = serializers.CharField()
    trend = AnalyticsPatternTrendBucketSerializer(many=True)
    status_distribution = AnalyticsPatternStatusDistributionBucketSerializer(many=True)
    establishments = AnalyticsPatternEstablishmentDistributionBucketSerializer(many=True)
    establishment_bucket_count = serializers.IntegerField()
    establishment_other_signal_count = serializers.IntegerField()
    responsible_business_units = AnalyticsPatternBusinessUnitDistributionBucketSerializer(
        many=True
    )
    business_unit_bucket_count = serializers.IntegerField()
    business_unit_other_signal_count = serializers.IntegerField()
    drilldown_context = AnalyticsPatternDrilldownContextSerializer()


class AnalyticsSignalEstablishmentRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()


class AnalyticsSignalBusinessUnitRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    specific_name = serializers.CharField()


class AnalyticsPatternSignalItemSerializer(serializers.Serializer):
    signal_id = serializers.UUIDField()
    title = serializers.CharField()
    structured_summary = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    resolved_at = serializers.DateTimeField(allow_null=True)
    establishment = AnalyticsSignalEstablishmentRefSerializer()
    responsible_business_unit = AnalyticsSignalBusinessUnitRefSerializer(allow_null=True)


class AnalyticsPatternSignalsResponseSerializer(serializers.Serializer):
    period = AnalyticsPeriodSerializer()
    items = AnalyticsPatternSignalItemSerializer(many=True)
    page_size = serializers.IntegerField()
    has_more = serializers.BooleanField()
    next_cursor = serializers.CharField(allow_null=True)


class AnalyticsPatternRenameRequestSerializer(serializers.Serializer):
    label = serializers.CharField(allow_blank=True)


class AnalyticsPatternMergeRequestSerializer(serializers.Serializer):
    target_pattern_id = serializers.UUIDField()


class AnalyticsPatternMoveSignalsRequestSerializer(serializers.Serializer):
    target_pattern_id = serializers.UUIDField()
    signal_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
    )


class AnalyticsPatternSplitToExistingRequestSerializer(
    AnalyticsPatternMoveSignalsRequestSerializer
):
    pass


class AnalyticsPatternSplitToNewRequestSerializer(serializers.Serializer):
    label = serializers.CharField(allow_blank=True)
    signal_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
    )


class AnalyticsOwnerGovernancePatternRefSerializer(serializers.Serializer):
    pattern_id = serializers.UUIDField()
    label = serializers.CharField()
    normalized_label = serializers.CharField()
    status = serializers.CharField()
    merged_into_pattern_id = serializers.UUIDField(allow_null=True)


class AnalyticsOwnerGovernanceResponseSerializer(serializers.Serializer):
    source_pattern = AnalyticsOwnerGovernancePatternRefSerializer()
    target_pattern = AnalyticsOwnerGovernancePatternRefSerializer(allow_null=True)
    moved_signal_count = serializers.IntegerField()
    target_created = serializers.BooleanField()
