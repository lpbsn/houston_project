from __future__ import annotations

from django.db import models
from django.db.models import Q

from houston.core.models import BaseModel
from houston.signals.constants import (
    ACTIVE_SIGNAL_STATUSES,
    AI_ISSUE_FOCUS_MAX_LENGTH,
    SIGNAL_LOCATION_TEXT_MAX_LENGTH,
    SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH,
    SIGNAL_TITLE_MAX_LENGTH,
)


class ExpectedAction(models.TextChoices):
    CLEAN_SECURE = "clean_secure", "Clean / secure"
    REPAIR = "repair", "Repair"
    REPLENISH = "replenish", "Replenish"
    INSPECT = "inspect", "Inspect"
    COORDINATE = "coordinate", "Coordinate"
    ASSIST = "assist", "Assist"
    INFORM = "inform", "Inform"
    MONITOR = "monitor", "Monitor"
    SAFETY_RESPONSE = "safety_response", "Safety response"


class Signal(BaseModel):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        INTERESTING = "interesting", "Interesting"
        IN_PROGRESS = "in_progress", "In progress"
        RESOLVED = "resolved", "Resolved"
        CANCELED = "canceled", "Canceled"
        ARCHIVED = "archived", "Archived"

    class RoutingStatus(models.TextChoices):
        RESOLVED = "resolved", "Resolved"
        UNASSIGNED = "unassigned", "Unassigned"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="signals",
    )
    affected_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="affected_signals",
        null=True,
        blank=True,
    )
    responsible_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="responsible_signals",
        null=True,
        blank=True,
    )
    activity_subject = models.ForeignKey(
        "establishments.ActivitySubject",
        on_delete=models.PROTECT,
        related_name="signals",
        null=True,
        blank=True,
    )
    operational_unit = models.ForeignKey(
        "establishments.OperationalUnit",
        on_delete=models.PROTECT,
        related_name="signals",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    # No model/DB default: every create path must set routing_status explicitly.
    routing_status = models.CharField(
        max_length=20,
        choices=RoutingStatus.choices,
    )
    expected_action = models.CharField(
        max_length=32,
        choices=ExpectedAction.choices,
        null=True,
        blank=True,
    )
    is_pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)
    pinned_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.SET_NULL,
        related_name="pinned_signals",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=SIGNAL_TITLE_MAX_LENGTH)
    structured_summary = models.TextField(max_length=SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH)
    location_text = models.CharField(
        max_length=SIGNAL_LOCATION_TEXT_MAX_LENGTH,
        blank=True,
        default="",
    )
    issue_focus = models.CharField(
        max_length=AI_ISSUE_FOCUS_MAX_LENGTH,
        blank=True,
        default="",
    )
    merged_into = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="merged_sources",
        null=True,
        blank=True,
    )
    last_activity_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "establishment",
                    "status",
                    "is_pinned",
                    "last_activity_at",
                ],
                name="signal_feed_sort_idx",
            ),
            models.Index(
                fields=["establishment", "affected_business_unit"],
                name="signal_est_affected_bu_idx",
            ),
            models.Index(
                fields=["establishment", "responsible_business_unit"],
                name="signal_est_responsible_bu_idx",
            ),
            models.Index(
                fields=["establishment", "activity_subject"],
                name="signal_est_act_subject_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "establishment",
                    "affected_business_unit",
                    "responsible_business_unit",
                    "activity_subject",
                    "operational_unit",
                    "issue_focus",
                ],
                condition=Q(status__in=ACTIVE_SIGNAL_STATUSES)
                & Q(routing_status="resolved"),
                name="signal_unique_active_aggregation_key",
                nulls_distinct=False,
            ),
        ]

    def __str__(self) -> str:
        return f"Signal {self.id} [{self.status}]"


class CandidateSignal(BaseModel):
    class Outcome(models.TextChoices):
        PENDING = "pending", "Pending"
        CREATED_SIGNAL = "created_signal", "Created signal"
        AGGREGATED_SIGNAL = "aggregated_signal", "Aggregated signal"
        REJECTED = "rejected", "Rejected"
        NO_SIGNAL_CREATED = "no_signal_created", "No signal created"

    class SignalKind(models.TextChoices):
        ACTIONABLE = "actionable", "Actionable"
        INFORMATIONAL = "informational", "Informational"

    observation = models.ForeignKey(
        "observations.Observation",
        on_delete=models.CASCADE,
        related_name="candidate_signals",
    )
    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="candidate_signals",
    )
    affected_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="affected_candidate_signals",
        null=True,
        blank=True,
    )
    responsible_business_unit = models.ForeignKey(
        "establishments.BusinessUnit",
        on_delete=models.PROTECT,
        related_name="responsible_candidate_signals",
        null=True,
        blank=True,
    )
    activity_subject = models.ForeignKey(
        "establishments.ActivitySubject",
        on_delete=models.PROTECT,
        related_name="candidate_signals",
        null=True,
        blank=True,
    )
    location_text = models.CharField(
        max_length=SIGNAL_LOCATION_TEXT_MAX_LENGTH,
        blank=True,
        default="",
    )
    operational_unit = models.ForeignKey(
        "establishments.OperationalUnit",
        on_delete=models.PROTECT,
        related_name="candidate_signals",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=SIGNAL_TITLE_MAX_LENGTH, blank=True, default="")
    structured_summary = models.TextField(
        max_length=SIGNAL_STRUCTURED_SUMMARY_MAX_LENGTH,
        blank=True,
        default="",
    )
    issue_focus = models.CharField(
        max_length=AI_ISSUE_FOCUS_MAX_LENGTH,
        blank=True,
        default="",
    )
    schema_version = models.CharField(max_length=80, blank=True, default="")
    signal_kind = models.CharField(
        max_length=32,
        choices=SignalKind.choices,
        null=True,
        blank=True,
    )
    information_type = models.CharField(max_length=64, blank=True, default="")
    canonical_object = models.CharField(max_length=255, blank=True, default="")
    expected_action = models.CharField(
        max_length=32,
        choices=ExpectedAction.choices,
        null=True,
        blank=True,
    )
    proposed_affected_business_unit_routing_key = models.CharField(
        max_length=180,
        blank=True,
        default="",
    )
    proposed_responsible_business_unit_routing_key = models.CharField(
        max_length=180,
        blank=True,
        default="",
    )
    proposed_activity_subject_routing_key = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )
    routing_status = models.CharField(
        max_length=20,
        choices=Signal.RoutingStatus.choices,
        null=True,
        blank=True,
    )
    resolution_audit = models.JSONField(default=dict, blank=True)
    rejection_code = models.CharField(max_length=80, blank=True, default="")
    outcome = models.CharField(
        max_length=32,
        choices=Outcome.choices,
        default=Outcome.PENDING,
    )
    result_signal = models.ForeignKey(
        Signal,
        on_delete=models.SET_NULL,
        related_name="source_candidates",
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["observation", "outcome"],
                name="cand_signal_obs_outcome_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"CandidateSignal {self.id} [{self.outcome}]"


class SignalSourceObservation(BaseModel):
    class LinkType(models.TextChoices):
        CREATED_FROM = "created_from", "Created from"
        AGGREGATED_FROM = "aggregated_from", "Aggregated from"
        MERGED_FROM = "merged_from", "Merged from"

    signal = models.ForeignKey(
        Signal,
        on_delete=models.CASCADE,
        related_name="source_observation_links",
    )
    observation = models.ForeignKey(
        "observations.Observation",
        on_delete=models.CASCADE,
        related_name="linked_signals",
    )
    link_type = models.CharField(max_length=32, choices=LinkType.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["signal", "observation", "link_type"],
                name="signal_source_obs_unique_link",
            ),
        ]
        indexes = [
            models.Index(fields=["signal"], name="signal_src_obs_signal_idx"),
            models.Index(fields=["observation"], name="signal_src_obs_obs_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.signal_id} <- {self.observation_id} ({self.link_type})"


class SignalResolutionRequest(BaseModel):
    class ReviewRoute(models.TextChoices):
        STAFF_TO_MANAGER = "staff_to_manager", "Staff to manager"
        MANAGER_TO_DIRECTOR = "manager_to_director", "Manager to director"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELED = "canceled", "Canceled"

    class CanceledReason(models.TextChoices):
        CANCELED_BY_REQUESTER = "canceled_by_requester", "Canceled by requester"
        SIGNAL_RESOLVED_ELSEWHERE = (
            "signal_resolved_elsewhere",
            "Signal resolved elsewhere",
        )
        SIGNAL_CANCELED = "signal_canceled", "Signal canceled"
        SIGNAL_MARKED_INTERESTING = (
            "signal_marked_interesting",
            "Signal marked interesting",
        )
        ACTION_PLAN_CREATED = "action_plan_created", "Action plan created"
        SIGNAL_NO_LONGER_OPEN = "signal_no_longer_open", "Signal no longer open"

    signal = models.ForeignKey(
        Signal,
        on_delete=models.CASCADE,
        related_name="resolution_requests",
    )
    requested_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="signal_resolution_requests_created",
    )
    requested_at = models.DateTimeField()
    review_route = models.CharField(max_length=32, choices=ReviewRoute.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    request_comment = models.TextField(blank=True, default="")
    reviewed_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="signal_resolution_requests_reviewed",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_comment = models.TextField(blank=True, default="")
    canceled_at = models.DateTimeField(null=True, blank=True)
    canceled_reason = models.CharField(
        max_length=40,
        choices=CanceledReason.choices,
        blank=True,
        default="",
    )
    cancel_comment = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["signal"],
                condition=Q(status="pending"),
                name="signal_resolution_req_pending_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["signal", "status"], name="sig_res_req_signal_status_idx"),
            models.Index(
                fields=["review_route", "status"],
                name="sig_res_req_route_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"SignalResolutionRequest {self.id} [{self.status}]"
