from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from houston.analytics.models import PATTERN_ISSUE_COMMENT_MAX_LENGTH


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


class AnalyticsDashboardMetricComparisonSerializer(AnalyticsMetricComparisonSerializer):
    coverage = serializers.ChoiceField(choices=["complete", "partial", "not_comparable"])


class AnalyticsDelayStatsSerializer(serializers.Serializer):
    median_seconds = serializers.FloatField(allow_null=True)
    mean_seconds = serializers.FloatField(allow_null=True)
    p90_seconds = serializers.FloatField(allow_null=True)
    n = serializers.IntegerField()
    comparison = AnalyticsDashboardMetricComparisonSerializer()


class AnalyticsRecurringPatternItemSerializer(serializers.Serializer):
    pattern_id = serializers.UUIDField()
    name = serializers.CharField()
    signal_count = serializers.IntegerField()
    comparison = AnalyticsDashboardMetricComparisonSerializer()


class AnalyticsNewPatternItemSerializer(serializers.Serializer):
    pattern_id = serializers.UUIDField()
    name = serializers.CharField()
    first_seen_at = serializers.DateTimeField()
    observation_count = serializers.IntegerField()
    establishment_count = serializers.IntegerField(allow_null=True)
    establishment_id = serializers.UUIDField(allow_null=True)
    establishment_name = serializers.CharField(allow_null=True)


class AnalyticsContributorItemSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    name = serializers.CharField()
    pts = serializers.IntegerField()
    roles = serializers.ListField(child=serializers.CharField())
    poles = serializers.ListField(child=serializers.CharField())


class AnalyticsAgingBucketSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    share = serializers.FloatField(allow_null=True)


class AnalyticsNamedCountItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    count = serializers.IntegerField()
    establishment_id = serializers.UUIDField(allow_null=True)
    establishment_name = serializers.CharField(allow_null=True)
    comparison = AnalyticsDashboardMetricComparisonSerializer()


class AnalyticsDeadlineShareSerializer(serializers.Serializer):
    early = serializers.FloatField(allow_null=True)
    on_time = serializers.FloatField(allow_null=True)
    late = serializers.FloatField(allow_null=True)
    n = serializers.IntegerField()
    early_comparison = AnalyticsDashboardMetricComparisonSerializer()
    on_time_comparison = AnalyticsDashboardMetricComparisonSerializer()
    late_comparison = AnalyticsDashboardMetricComparisonSerializer()


class AnalyticsDashboardResponseSerializer(serializers.Serializer):
    period_days = serializers.IntegerField()
    current_period = AnalyticsPeriodSerializer()
    previous_period = AnalyticsPeriodSerializer()
    history_reliable_from = serializers.DateTimeField()
    scope_type = serializers.ChoiceField(choices=["cross", "establishment"])
    establishment_id = serializers.UUIDField(allow_null=True)
    establishment_ids = serializers.ListField(child=serializers.UUIDField())
    recurring_patterns = AnalyticsRecurringPatternItemSerializer(many=True)
    new_patterns = AnalyticsNewPatternItemSerializer(many=True)
    new_patterns_preview_limit = serializers.IntegerField()
    contributors = AnalyticsContributorItemSerializer(many=True)
    observation_delay_canceled = AnalyticsDelayStatsSerializer()
    observation_delay_resolved = AnalyticsDelayStatsSerializer()
    observation_delay_transformed = AnalyticsDelayStatsSerializer()
    operational_resolution_rate = AnalyticsDashboardMetricComparisonSerializer()
    closure_resolved_share = AnalyticsDashboardMetricComparisonSerializer()
    reopenings = AnalyticsDashboardMetricComparisonSerializer()
    open_observation_count = serializers.IntegerField()
    aging_buckets = AnalyticsAgingBucketSerializer(many=True)
    aging_over_15d_share = AnalyticsDashboardMetricComparisonSerializer()
    plan_delay_canceled = AnalyticsDelayStatsSerializer()
    plan_delay_resolved = AnalyticsDelayStatsSerializer()
    plan_validation = AnalyticsDelayStatsSerializer()
    plan_deadlines = AnalyticsDeadlineShareSerializer()
    zones = AnalyticsNamedCountItemSerializer(many=True)
    zones_preview_limit = serializers.IntegerField()
    poles = AnalyticsNamedCountItemSerializer(many=True)


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


@extend_schema_field(
    {
        "type": "string",
        "enum": ["wrong_pattern"],
    }
)
class AnalyticsPatternIssueReasonField(serializers.CharField):
    pass


@extend_schema_field(
    {
        "type": "string",
        "maxLength": PATTERN_ISSUE_COMMENT_MAX_LENGTH,
    }
)
class AnalyticsPatternIssueCommentField(serializers.CharField):
    pass


class AnalyticsPatternIssueReportRequestSerializer(serializers.Serializer):
    reason = AnalyticsPatternIssueReasonField(required=False, allow_blank=True)
    comment = AnalyticsPatternIssueCommentField(
        required=False,
        allow_blank=True,
    )


class AnalyticsPatternIssueReportResponseSerializer(serializers.Serializer):
    report_id = serializers.UUIDField()
    pattern_id = serializers.UUIDField()
    signal_id = serializers.UUIDField(allow_null=True)
    status = serializers.CharField()
    report_type = serializers.CharField()
    comment = serializers.CharField()
    created_at = serializers.DateTimeField()


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


class AnalyticsOwnerGovernanceTargetListResponseSerializer(serializers.Serializer):
    items = AnalyticsOwnerGovernancePatternRefSerializer(many=True)
    page_size = serializers.IntegerField()
    has_more = serializers.BooleanField()
    next_cursor = serializers.CharField(allow_null=True)
