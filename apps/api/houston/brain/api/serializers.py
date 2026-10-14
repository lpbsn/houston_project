from __future__ import annotations

from rest_framework import serializers


class BrainNoticeSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()


class BrainPersonSerializer(serializers.Serializer):
    id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()


class BrainExtractionSummarySerializer(serializers.Serializer):
    coverage = serializers.CharField()
    warnings = BrainNoticeSerializer(many=True)
    limits = BrainNoticeSerializer(many=True)
    measure_count = serializers.IntegerField()
    qualitative_count = serializers.IntegerField()


class BrainReportingResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    original_filename = serializers.CharField()
    source_format = serializers.CharField()
    byte_size = serializers.IntegerField()
    status = serializers.CharField()
    rejection_code = serializers.CharField()
    rejection_message = serializers.CharField()
    period_start = serializers.DateField(allow_null=True)
    period_end = serializers.DateField(allow_null=True)
    period_confirmed = serializers.BooleanField()
    author = BrainPersonSerializer()
    created_at = serializers.DateTimeField()
    extraction = BrainExtractionSummarySerializer()
    preview_url = serializers.CharField(required=False)


class BrainReportingListSerializer(serializers.Serializer):
    results = BrainReportingResponseSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class BrainPeriodRequestSerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()


class BrainReportingRefSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    original_filename = serializers.CharField()
    period_start = serializers.DateField(allow_null=True)
    period_end = serializers.DateField(allow_null=True)


class BrainAnalysisSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    failure_code = serializers.CharField()
    failure_message = serializers.CharField()
    author = BrainPersonSerializer()
    created_at = serializers.DateTimeField()
    reporting = BrainReportingRefSerializer()


class BrainAnalysisListSerializer(serializers.Serializer):
    results = BrainAnalysisSummarySerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class BrainWorkSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["analysis", "follow_up"])
    id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    status = serializers.CharField()
    reporting_id = serializers.UUIDField()


class BrainLaunchRequestSerializer(serializers.Serializer):
    reporting_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(max_length=128)


class BrainLaunchResponseSerializer(serializers.Serializer):
    matched = serializers.ChoiceField(choices=["request", "active"])
    work = BrainWorkSerializer()


class BrainActiveWorkSerializer(serializers.Serializer):
    work = BrainWorkSerializer(allow_null=True)


class BrainCancelResponseSerializer(serializers.Serializer):
    status = serializers.CharField()


class BrainSearchSerializer(serializers.Serializer):
    code = serializers.CharField()
    examined_count = serializers.IntegerField()
    retained_count = serializers.IntegerField()
    criteria = serializers.DictField()


class BrainDossierSummarySerializer(serializers.Serializer):
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    timezone = serializers.CharField()
    capture_started_at = serializers.DateTimeField()
    closed_at = serializers.DateTimeField(allow_null=True)


class BrainSuggestionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    action_plan_id = serializers.UUIDField(allow_null=True)
    current_revision_id = serializers.UUIDField(allow_null=True)
    title = serializers.CharField()
    description = serializers.CharField()
    tasks = serializers.ListField(child=serializers.DictField())
    pilot_business_unit_id = serializers.UUIDField(allow_null=True)
    assignees = serializers.ListField(child=serializers.DictField())
    start_at = serializers.DateTimeField(allow_null=True)
    end_at = serializers.DateTimeField(allow_null=True)
    occurrence_date = serializers.DateField(allow_null=True)
    all_day = serializers.BooleanField()
    requires_validation = serializers.BooleanField()


class BrainEvaluationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    objective_id = serializers.UUIDField()
    revision_id = serializers.UUIDField()
    indicator = serializers.CharField()
    outcome = serializers.CharField()
    reason = serializers.CharField()
    measured_period_start = serializers.DateField()
    measured_period_end = serializers.DateField()
    source_item_ids = serializers.ListField(child=serializers.CharField())
    is_current_bilan = serializers.BooleanField()


class BrainGlobalRepresentationSerializer(serializers.Serializer):
    formulation = serializers.CharField()
    conditions = serializers.CharField()
    limits = serializers.CharField()
    uncertainty = serializers.CharField()


class BrainMechanismSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    formulation = serializers.CharField()
    global_representation = BrainGlobalRepresentationSerializer()
    private_evidence_item_ids = serializers.ListField(child=serializers.CharField())
    knowledge_version_id = serializers.UUIDField(allow_null=True)


class BrainMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    request_id = serializers.CharField()
    sequence = serializers.IntegerField()
    purpose = serializers.CharField()
    body = serializers.CharField()
    status = serializers.CharField()
    failure_code = serializers.CharField()
    failure_message = serializers.CharField()
    author = BrainPersonSerializer()
    created_at = serializers.DateTimeField()
    declaration = serializers.JSONField(allow_null=True)
    result = serializers.JSONField(allow_null=True)


class BrainAnalysisDetailSerializer(BrainAnalysisSummarySerializer):
    claimed_at = serializers.DateTimeField(allow_null=True)
    result = serializers.JSONField(allow_null=True)
    dossier = BrainDossierSummarySerializer(allow_null=True)
    searches = BrainSearchSerializer(many=True)
    messages = BrainMessageSerializer(many=True)
    older_message_count = serializers.IntegerField()
    suggestions = BrainSuggestionSerializer(many=True)
    evaluations = BrainEvaluationSerializer(many=True)
    mechanisms = BrainMechanismSerializer(many=True)


class BrainFollowUpRequestSerializer(serializers.Serializer):
    request_id = serializers.CharField(max_length=128)
    body = serializers.CharField()
    purpose = serializers.ChoiceField(
        choices=["explain", "hypothesis", "correction", "new_fact", "new_document"]
    )
    cited_item_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )


class BrainFollowUpResponseSerializer(serializers.Serializer):
    matched = serializers.ChoiceField(choices=["request", "active"])
    work = BrainWorkSerializer()


class BrainSourcePageSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.DictField())
    next_cursor = serializers.CharField(allow_null=True)


class BrainDossierItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    category = serializers.CharField()
    role = serializers.CharField()
    reason = serializers.CharField()
    stable_key = serializers.CharField()
    payload = serializers.JSONField()


class BrainSuggestionRevisionRequestSerializer(serializers.Serializer):
    expected_revision_id = serializers.UUIDField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    tasks = serializers.ListField(child=serializers.DictField(), required=False)
    pilot_business_unit_id = serializers.UUIDField(required=False, allow_null=True)
    assignees = serializers.ListField(child=serializers.DictField(), required=False)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)
    occurrence_date = serializers.DateField(required=False, allow_null=True)
    all_day = serializers.BooleanField(required=False, default=False)
    requires_validation = serializers.BooleanField(required=False, default=True)


class BrainSuggestionConvertRequestSerializer(serializers.Serializer):
    expected_revision_id = serializers.UUIDField()


class BrainSuggestionConvertResponseSerializer(serializers.Serializer):
    action_plan_id = serializers.UUIDField()
    created = serializers.BooleanField()
    related_plan_ids = serializers.ListField(child=serializers.UUIDField())


class BrainBilanSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    analysis_id = serializers.UUIDField()
    revision_id = serializers.UUIDField()
    measured_period_start = serializers.DateField()
    measured_period_end = serializers.DateField()
    outcome = serializers.CharField()
    reason = serializers.CharField()


class BrainObjectiveSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    current_revision_id = serializers.UUIDField()
    indicator = serializers.CharField()
    unit = serializers.CharField()
    scope = serializers.CharField()
    reference = serializers.CharField()
    target = serializers.CharField()
    due_on = serializers.DateField(allow_null=True)
    method = serializers.CharField()
    decision = serializers.CharField()
    current_bilan = BrainBilanSerializer(allow_null=True)


class BrainObjectiveListSerializer(serializers.Serializer):
    results = BrainObjectiveSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)


class BrainObjectiveDecisionRequestSerializer(serializers.Serializer):
    expected_revision_id = serializers.UUIDField()
    decision = serializers.ChoiceField(choices=["accepted", "modified", "refused"])
    indicator = serializers.CharField(required=False, allow_blank=True)
    unit = serializers.CharField(required=False, allow_blank=True)
    scope = serializers.CharField(required=False, allow_blank=True)
    reference = serializers.CharField(required=False, allow_blank=True)
    target = serializers.CharField(required=False, allow_blank=True)
    success_condition = serializers.ChoiceField(
        choices=["", "eq", "gt", "gte", "lt", "lte", "qualitative"],
        required=False,
        allow_blank=True,
    )
    due_on = serializers.DateField(required=False, allow_null=True)
    measurement_period_start = serializers.DateField(required=False, allow_null=True)
    measurement_period_end = serializers.DateField(required=False, allow_null=True)
    method = serializers.CharField(required=False, allow_blank=True)
    justification = serializers.CharField(required=False, allow_blank=True, default="")


class BrainMechanismRevisionRequestSerializer(serializers.Serializer):
    formulation = serializers.CharField()
    conditions = serializers.CharField(required=False, allow_blank=True, default="")
    limits = serializers.CharField(required=False, allow_blank=True, default="")
    uncertainty = serializers.CharField(required=False, allow_blank=True, default="")


class BrainPlatformRepresentationSerializer(serializers.Serializer):
    formulation = serializers.CharField()
    conditions = serializers.CharField()
    limits = serializers.CharField()
    uncertainty = serializers.CharField()
    withheld = serializers.DictField()


class BrainPlatformMechanismSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    status = serializers.CharField()
    knowledge_version_id = serializers.UUIDField(allow_null=True)
    is_active = serializers.BooleanField()
    representation = BrainPlatformRepresentationSerializer()


class BrainPlatformMechanismListSerializer(serializers.Serializer):
    results = BrainPlatformMechanismSerializer(many=True)


class BrainMechanismDecisionRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])


class BrainKnowledgeVersionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    formulation = serializers.CharField()
    conditions = serializers.CharField()
    limits = serializers.CharField()
    uncertainty = serializers.CharField()
    approved_at = serializers.DateTimeField(allow_null=True)
    activated_at = serializers.DateTimeField(allow_null=True)
    is_active = serializers.BooleanField()


class BrainKnowledgeVersionListSerializer(serializers.Serializer):
    results = BrainKnowledgeVersionSerializer(many=True)
