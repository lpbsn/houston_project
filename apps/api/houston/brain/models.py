from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from houston.core.models import BaseModel


class BrainReporting(BaseModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        REJECTED = "rejected", "Rejected"

    class SourceFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        PDF = "pdf", "PDF"
        DOCX = "docx", "DOCX"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_reportings",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authored_brain_reportings",
    )
    original_filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    source_format = models.CharField(max_length=16, choices=SourceFormat.choices)
    content_sha256 = models.CharField(max_length=64)
    storage_key = models.CharField(max_length=512)
    byte_size = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    rejection_code = models.CharField(max_length=80, blank=True, default="")
    rejection_message = models.TextField(blank=True, default="")
    # Civil window [period_start, period_end): start inclusive, end exclusive.
    # Lot 2 collection reads these dates in the establishment timezone.
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    period_confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    period_confirmed_at__isnull=True,
                    period_start__isnull=True,
                    period_end__isnull=True,
                )
                | (
                    Q(
                        period_confirmed_at__isnull=False,
                        period_start__isnull=False,
                        period_end__isnull=False,
                    )
                    & Q(period_end__gt=F("period_start"))
                ),
                name="brain_rep_period_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["establishment", "status", "created_at"],
                name="brain_rep_est_stat_cr_idx",
            ),
            models.Index(fields=["author"], name="brain_rep_author_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainReporting {self.id} [{self.status}]"


class BrainExtraction(BaseModel):
    reporting = models.ForeignKey(
        BrainReporting,
        on_delete=models.CASCADE,
        related_name="extractions",
    )
    extractor_id = models.CharField(max_length=80)
    extractor_version = models.CharField(max_length=40)
    source_sha256 = models.CharField(max_length=64)
    payload = models.JSONField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["reporting", "extractor_id", "extractor_version", "source_sha256"],
                name="brain_ext_version_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"BrainExtraction {self.extractor_id}@{self.extractor_version}"


class BrainAnalysis(BaseModel):
    """One explicit analysis request. Configuration is copied at admission and left unchanged."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_analyses",
    )
    reporting = models.ForeignKey(
        BrainReporting,
        on_delete=models.CASCADE,
        related_name="analyses",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authored_brain_analyses",
    )
    idempotency_key = models.CharField(max_length=128)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    attempt_token = models.UUIDField(default=uuid.uuid4)
    attempt_count = models.PositiveIntegerField(default=0)
    transient_retries_used = models.PositiveIntegerField(default=0)
    transport_republish_count = models.PositiveIntegerField(default=0)
    transport_stall_since = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True, default="")
    reserved_input_tokens = models.PositiveIntegerField(default=0)
    consumed_input_tokens = models.PositiveIntegerField(default=0)
    provider_calls_used = models.PositiveIntegerField(default=0)
    configuration = models.JSONField()
    result = models.JSONField(null=True, blank=True)
    # Tool name, arguments, and returned copy ids, in order. Texts stay on the dossier.
    trace = models.JSONField(default=list, blank=True)
    # Reporting, period, copied mechanisms, and joined contributions. Blank on rows
    # admitted before this identity existed; those rows do not block a new launch.
    context_fingerprint = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment", "idempotency_key"],
                name="brain_an_est_idem_uniq",
            ),
            models.UniqueConstraint(
                fields=["establishment", "context_fingerprint"],
                condition=Q(status__in=["queued", "running", "completed"])
                & ~Q(context_fingerprint=""),
                name="brain_an_ctx_live_uniq",
            ),
            models.UniqueConstraint(
                fields=["establishment"],
                condition=Q(status="running"),
                name="brain_an_one_running",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "queued",
                        "running",
                        "completed",
                        "failed",
                        "canceled",
                    ]
                ),
                name="brain_an_status_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["author"], name="brain_an_author_idx"),
            models.Index(fields=["status", "created_at"], name="brain_an_stat_cr_idx"),
            models.Index(
                fields=["establishment", "status", "created_at"],
                name="brain_an_est_stat_cr_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"BrainAnalysis {self.id} [{self.status}]"


class BrainCapacity(models.Model):
    """Single lock row. Admission locks it and releases the lock at commit."""

    singleton_key = models.PositiveSmallIntegerField(primary_key=True, default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(singleton_key=1),
                name="brain_capacity_singleton",
            ),
        ]

    def __str__(self) -> str:
        return "BrainCapacity"


class BrainMessage(BaseModel):
    """One follow-up on a completed analysis. Its status and budgets are not the analysis."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    class Purpose(models.TextChoices):
        EXPLAIN = "explain", "Explain"
        HYPOTHESIS = "hypothesis", "Hypothesis"
        CORRECTION = "correction", "Correction"
        NEW_FACT = "new_fact", "New fact"
        NEW_DOCUMENT = "new_document", "New document"

    analysis = models.ForeignKey(
        BrainAnalysis,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authored_brain_messages",
    )
    request_id = models.CharField(max_length=128)
    sequence = models.PositiveIntegerField()
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    body = models.TextField()
    cited_item_ids = models.JSONField(default=list)
    declaration = models.JSONField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.QUEUED,
    )
    attempt_token = models.UUIDField(default=uuid.uuid4)
    attempt_count = models.PositiveIntegerField(default=0)
    transient_retries_used = models.PositiveIntegerField(default=0)
    transport_republish_count = models.PositiveIntegerField(default=0)
    transport_stall_since = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=80, blank=True, default="")
    reserved_input_tokens = models.PositiveIntegerField(default=0)
    consumed_input_tokens = models.PositiveIntegerField(default=0)
    provider_calls_used = models.PositiveIntegerField(default=0)
    result = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "request_id"],
                name="brain_msg_an_req_uniq",
            ),
            models.UniqueConstraint(
                fields=["analysis", "sequence"],
                name="brain_msg_an_seq_uniq",
            ),
            models.CheckConstraint(
                condition=Q(sequence__gte=1),
                name="brain_msg_seq_chk",
            ),
            models.CheckConstraint(
                condition=Q(
                    purpose__in=[
                        "explain",
                        "hypothesis",
                        "correction",
                        "new_fact",
                        "new_document",
                    ]
                ),
                name="brain_msg_purpose_chk",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "queued",
                        "running",
                        "completed",
                        "failed",
                        "canceled",
                    ]
                ),
                name="brain_msg_status_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="brain_msg_stat_cr_idx"),
            models.Index(fields=["author"], name="brain_msg_author_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainMessage {self.sequence} [{self.status}]"


class BrainSlot(BaseModel):
    """One active Brain work for an establishment. Uniqueness is the slot, not an analysis index."""

    class Kind(models.TextChoices):
        ANALYSIS = "analysis", "Analysis"
        FOLLOW_UP = "follow_up", "Follow-up"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_slots",
    )
    analysis = models.ForeignKey(
        BrainAnalysis,
        on_delete=models.CASCADE,
        related_name="slots",
    )
    message = models.ForeignKey(
        BrainMessage,
        on_delete=models.CASCADE,
        related_name="slots",
        null=True,
        blank=True,
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices)
    token = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment"],
                condition=Q(status__in=["queued", "running"]),
                name="brain_slot_one_active",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=["analysis", "follow_up"]),
                name="brain_slot_kind_chk",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["queued", "running"]),
                name="brain_slot_status_chk",
            ),
            models.CheckConstraint(
                condition=Q(kind="analysis", message__isnull=True)
                | Q(kind="follow_up", message__isnull=False),
                name="brain_slot_msg_kind_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["analysis"], name="brain_slot_analysis_idx"),
            models.Index(fields=["message"], name="brain_slot_message_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainSlot {self.establishment_id} [{self.kind}/{self.status}]"


class BrainDossier(BaseModel):
    """Frozen capture. closed_at is written with the items; nothing is rewritten after that."""

    analysis = models.OneToOneField(
        BrainAnalysis,
        on_delete=models.CASCADE,
        related_name="dossier",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_dossiers",
    )
    timezone = models.CharField(max_length=63)
    period_start = models.DateField()
    period_end = models.DateField()
    capture_started_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(period_end__gt=F("period_start")),
                name="brain_dos_period_chk",
            ),
        ]

    def __str__(self) -> str:
        state = "closed" if self.closed_at else "open"
        return f"BrainDossier {self.analysis_id} [{state}]"


class BrainDossierItem(BaseModel):
    """Copied source. source identity lives in the payload, with no cascade back to the live row."""

    dossier = models.ForeignKey(
        BrainDossier,
        on_delete=models.CASCADE,
        related_name="items",
    )
    category = models.CharField(max_length=32)
    stable_key = models.CharField(max_length=96)
    role = models.CharField(max_length=32)
    payload = models.JSONField()
    reason = models.CharField(max_length=80, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dossier", "stable_key"],
                name="brain_item_dos_key_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["dossier", "category"], name="brain_item_dos_cat_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainDossierItem {self.category}:{self.stable_key}"


class BrainSearchRun(BaseModel):
    """One executed search, including a search that retained nothing."""

    dossier = models.ForeignKey(
        BrainDossier,
        on_delete=models.CASCADE,
        related_name="search_runs",
    )
    code = models.CharField(max_length=64)
    criteria = models.JSONField()
    examined_count = models.PositiveIntegerField()
    retained_count = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dossier", "code"],
                name="brain_search_dos_code_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"BrainSearchRun {self.code} {self.retained_count}/{self.examined_count}"


class BrainObjective(BaseModel):
    """Living objective. The bilan points at an evaluation and does not rewrite a revision."""

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_objectives",
    )
    current_revision = models.ForeignKey(
        "BrainObjectiveRevision",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    current_bilan = models.ForeignKey(
        "BrainObjectiveEvaluation",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["establishment"], name="brain_obj_est_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainObjective {self.id}"


class BrainObjectiveRevision(BaseModel):
    objective = models.ForeignKey(
        BrainObjective,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_objective_revisions",
    )
    indicator = models.CharField(max_length=255)
    unit = models.CharField(max_length=64, blank=True, default="")
    scope = models.CharField(max_length=255, blank=True, default="")
    reference = models.CharField(max_length=255, blank=True, default="")
    target = models.CharField(max_length=255, blank=True, default="")
    success_condition = models.CharField(max_length=32, blank=True, default="")
    due_on = models.DateField(null=True, blank=True)
    measurement_period_start = models.DateField(null=True, blank=True)
    measurement_period_end = models.DateField(null=True, blank=True)
    method = models.TextField(blank=True, default="")
    content_hash = models.CharField(max_length=64)
    decision = models.CharField(max_length=16, default="recorded")
    justification = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    measurement_period_start__isnull=True,
                    measurement_period_end__isnull=True,
                )
                | Q(
                    measurement_period_start__isnull=False,
                    measurement_period_end__isnull=False,
                    measurement_period_end__gt=F("measurement_period_start"),
                ),
                name="brain_rev_measure_chk",
            ),
            models.CheckConstraint(
                condition=Q(decision__in=["recorded", "accepted", "modified", "refused"]),
                name="brain_rev_decision_chk",
            ),
            models.CheckConstraint(
                condition=Q(
                    success_condition__in=["", "eq", "gt", "gte", "lt", "lte", "qualitative"]
                ),
                name="brain_rev_cond_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["objective", "created_at"], name="brain_rev_obj_cr_idx"),
            models.Index(fields=["establishment", "created_at"], name="brain_rev_est_cr_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainObjectiveRevision {self.id}"


class BrainLot(BaseModel):
    """One validated section batch. Reuse compares input and frozen configuration hashes."""

    class Status(models.TextChoices):
        VALIDATED = "validated", "Validated"

    analysis = models.ForeignKey(
        BrainAnalysis,
        on_delete=models.CASCADE,
        related_name="lots",
    )
    stable_key = models.CharField(max_length=64)
    input_hash = models.CharField(max_length=64)
    configuration_hash = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices)
    output = models.JSONField()
    attempt_token = models.UUIDField()
    reserved_input_tokens = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "stable_key"],
                name="brain_lot_an_key_uniq",
            ),
            models.CheckConstraint(
                condition=Q(status="validated"),
                name="brain_lot_status_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["analysis", "status"],
                name="brain_lot_an_stat_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"BrainLot {self.stable_key} [{self.status}]"


class BrainWorkerBeat(models.Model):
    """One Brain worker process. A fresh beat shows that this process is alive."""

    process_name = models.CharField(max_length=200, primary_key=True)
    beat_at = models.DateTimeField()
    concurrency = models.PositiveIntegerField()
    in_flight = models.PositiveIntegerField()

    class Meta:
        indexes = [
            models.Index(fields=["beat_at"], name="brain_beat_at_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainWorkerBeat {self.process_name} {self.in_flight}/{self.concurrency}"


class BrainSuggestion(BaseModel):
    """Editable plan draft. Conversion stores the Houston plan id without a cascade."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CONVERTED = "converted", "Converted"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_suggestions",
    )
    analysis = models.ForeignKey(
        BrainAnalysis,
        on_delete=models.CASCADE,
        related_name="suggestions",
    )
    stable_key = models.CharField(max_length=80)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    current_revision = models.ForeignKey(
        "BrainSuggestionRevision",
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )
    action_plan_id = models.UUIDField(null=True, blank=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    converted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "stable_key"],
                name="brain_sug_an_key_uniq",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["draft", "converted"]),
                name="brain_sug_status_chk",
            ),
            models.CheckConstraint(
                condition=Q(status="draft", action_plan_id__isnull=True)
                | Q(status="converted", action_plan_id__isnull=False),
                name="brain_sug_plan_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["establishment", "status"], name="brain_sug_est_stat_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainSuggestion {self.stable_key} [{self.status}]"


class BrainSuggestionRevision(BaseModel):
    suggestion = models.ForeignKey(
        BrainSuggestion,
        on_delete=models.CASCADE,
        related_name="revisions",
    )
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    tasks = models.JSONField(default=list)
    pilot_business_unit_id = models.UUIDField(null=True, blank=True)
    assignees = models.JSONField(default=list)
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    occurrence_date = models.DateField(null=True, blank=True)
    all_day = models.BooleanField(default=False)
    requires_validation = models.BooleanField(default=True)
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="brain_suggestion_revisions",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["suggestion", "number"],
                name="brain_sugrev_num_uniq",
            ),
            models.CheckConstraint(
                condition=Q(number__gte=1),
                name="brain_sugrev_num_chk",
            ),
        ]

    def __str__(self) -> str:
        return f"BrainSuggestionRevision {self.suggestion_id}#{self.number}"


class BrainObjectiveEvaluation(BaseModel):
    """One reading of a captured revision. It does not rewrite that revision."""

    class Outcome(models.TextChoices):
        REACHED = "reached", "Reached"
        NOT_REACHED = "not_reached", "Not reached"
        NON_EVALUABLE = "non_evaluable", "Non evaluable"
        QUALITATIVE = "qualitative", "Qualitative"

    analysis = models.ForeignKey(
        BrainAnalysis,
        on_delete=models.CASCADE,
        related_name="objective_evaluations",
    )
    objective = models.ForeignKey(
        BrainObjective,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    revision = models.ForeignKey(
        BrainObjectiveRevision,
        on_delete=models.PROTECT,
        related_name="evaluations",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_objective_evaluations",
    )
    measured_period_start = models.DateField()
    measured_period_end = models.DateField()
    outcome = models.CharField(max_length=32, choices=Outcome.choices)
    reason = models.CharField(max_length=80, blank=True, default="")
    source_item_ids = models.JSONField(default=list)
    measure = models.JSONField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "revision"],
                name="brain_eval_an_rev_uniq",
            ),
            models.CheckConstraint(
                condition=Q(measured_period_end__gt=F("measured_period_start")),
                name="brain_eval_period_chk",
            ),
            models.CheckConstraint(
                condition=Q(outcome__in=["reached", "not_reached", "non_evaluable", "qualitative"]),
                name="brain_eval_outcome_chk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["objective", "measured_period_end"],
                name="brain_eval_obj_end_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"BrainObjectiveEvaluation {self.revision_id} [{self.outcome}]"


class BrainKnowledgeVersion(BaseModel):
    """Platform formulation. Approval does not activate it.

    Several versions may be active. Only one active row is allowed per identifier.
    """

    identifier = models.CharField(max_length=80, blank=True, default="")
    global_formulation = models.TextField()
    conditions = models.TextField(blank=True, default="")
    limits = models.TextField(blank=True, default="")
    uncertainty = models.TextField(blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["identifier"],
                condition=Q(is_active=True),
                name="brain_know_active_ident_uniq",
            ),
            models.CheckConstraint(
                condition=~Q(is_active=True) | Q(approved_at__isnull=False),
                name="brain_know_active_appr_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["approved_at"], name="brain_know_appr_idx"),
        ]

    def __str__(self) -> str:
        state = "active" if self.is_active else "inactive"
        return f"BrainKnowledgeVersion {self.id} [{state}]"


class BrainMechanismCandidate(BaseModel):
    """Client candidate. Platform reads the global formulation, not the private evidence."""

    class Status(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    analysis = models.ForeignKey(
        BrainAnalysis,
        on_delete=models.CASCADE,
        related_name="mechanism_candidates",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="brain_mechanism_candidates",
    )
    stable_key = models.CharField(max_length=80)
    formulation = models.TextField()
    global_formulation = models.TextField(blank=True, default="")
    conditions = models.TextField(blank=True, default="")
    limits = models.TextField(blank=True, default="")
    uncertainty = models.TextField(blank=True, default="")
    origin = models.CharField(max_length=32, default="analysis")
    private_evidence = models.JSONField(default=list)
    global_representation = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CANDIDATE,
    )
    knowledge_version = models.ForeignKey(
        BrainKnowledgeVersion,
        on_delete=models.PROTECT,
        related_name="candidates",
        null=True,
        blank=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["analysis", "stable_key"],
                name="brain_mech_an_key_uniq",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["candidate", "approved", "rejected"]),
                name="brain_mech_status_chk",
            ),
            models.CheckConstraint(
                condition=~Q(status="approved") | Q(knowledge_version__isnull=False),
                name="brain_mech_appr_ver_chk",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="brain_mech_stat_cr_idx"),
        ]

    def __str__(self) -> str:
        return f"BrainMechanismCandidate {self.stable_key} [{self.status}]"
