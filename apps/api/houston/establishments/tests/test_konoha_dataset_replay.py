from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from houston.action_plans.constants import EXECUTION_LIFECYCLE_EVENT_MARKED_DONE
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionLifecycleEvent,
)
from houston.analytics.models import AnalyticsHistoryCoverage, SignalPatternAssignment
from houston.establishments.business_unit_domain_service import create_onboarding_business_unit
from houston.establishments.business_unit_identity import (
    normalize_generic_activity_subject_name,
)
from houston.establishments.konoha_dataset_actors import (
    ESTABLISHMENT_AKATSUKI,
    ESTABLISHMENT_ANBU,
    NARUTO_EMAIL,
    NARUTO_USERNAME,
    ORGANIZATION_NAME,
    POLE_COMMERCE,
    POLE_HOTEL,
    POLE_ISHIRAKU,
    POLE_MAINTENANCE,
    POLE_YAKINUKU,
)
from houston.establishments.konoha_dataset_observations import (
    OCCURRED_AT_MAX,
    load_konoha_dataset_observations,
)
from houston.establishments.konoha_dataset_replay import (
    EVENT_MARK_INTERESTING,
    EVENT_PLAN_CANCEL,
    EVENT_PLAN_CREATE,
    EVENT_PLAN_MARK_DONE,
    EVENT_PLAN_PROMOTE,
    EVENT_PLAN_VALIDATE,
    EVENT_QUALIFY,
    EVENT_RESOLVE,
    EVENT_RR_APPROVE,
    EVENT_RR_CREATE,
    EVENT_RR_REJECT,
    EVENT_SUBMIT,
    FINGERPRINT_CONFLICT,
    FINGERPRINT_MATCH,
    FINGERPRINT_MISSING,
    KonohaDatasetReplayError,
    ReplayEvent,
    ReplayResult,
    ReplayRuntime,
    _event_fingerprint,
    _qualify_event,
    _resolve_event,
    _rr_create_event,
    _rr_reject_event,
    _submit_event,
    _suppress_replay_side_effects,
    _wipe_konoha_gamification_state,
    build_replay_events,
    freeze_django_now,
    load_replay_runtime,
    parse_corpus_datetime,
    remap_candidate_to_pipeline_output,
    replay_konoha_dataset_observations,
)
from houston.establishments.models import (
    ActivitySubject,
    CatalogActivitySubject,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.establishments.tests.test_provision_konoha_dataset_actors import (
    LOCAL_DATABASES,
    _create_named_user,
    _create_scoped_member,
)
from houston.gamification.models import GamificationSeason, PointTransaction
from houston.gamification.selectors import month_bounds_for_occurred_at
from houston.gamification.services import open_season
from houston.observations.models import Observation, ObservationProcessing
from houston.organizations.models import Organization
from houston.signals.constants import (
    SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
)
from houston.signals.models import CandidateSignal, Signal, SignalResolutionRequest
from houston.testing.factories import create_establishment
from houston.testing.taxonomy import create_business_unit

pytestmark = pytest.mark.django_db

MINI_CORPUS_IDS = ("anbu.hotel.01", "anbu.hotel.02", "anbu.hotel.03")


def _mini_corpus_rows() -> list[dict]:
    by_id = {row["id"]: row for row in load_konoha_dataset_observations()}
    return [by_id[corpus_id] for corpus_id in MINI_CORPUS_IDS]


def test_timeline_orders_submits_before_resolves_and_respects_cutoff():
    events = build_replay_events(_mini_corpus_rows(), overrides={})
    assert [event.kind for event in events] == [
        EVENT_SUBMIT,
        EVENT_SUBMIT,
        EVENT_PLAN_CREATE,
        EVENT_PLAN_MARK_DONE,
        EVENT_PLAN_VALIDATE,
        EVENT_SUBMIT,
        EVENT_RESOLVE,
    ]
    assert [event.corpus_id for event in events] == [
        "anbu.hotel.01",
        "anbu.hotel.02",
        "anbu.hotel.02",
        "anbu.hotel.02",
        "anbu.hotel.02",
        "anbu.hotel.03",
        "anbu.hotel.03",
    ]
    assert events[2].at == parse_corpus_datetime("2025-08-07T09:40:00+02:00")
    assert events[4].at == parse_corpus_datetime("2025-08-08T18:00:00+02:00")
    assert all(event.at <= OCCURRED_AT_MAX for event in events)

    same_instant = parse_corpus_datetime("2025-08-08T18:00:00+02:00")
    tied = [
        {
            **_mini_corpus_rows()[0],
            "id": "tie.submit",
            "occurred_at": same_instant.isoformat(),
            "signal_group": "tie.sg",
            "cycle": {
                "open_at_cutoff": False,
                "resolved_at": same_instant.isoformat(),
                "planned_action_at": None,
                "resolution": "manual",
            },
        }
    ]
    tied_events = build_replay_events(tied, overrides={})
    assert [event.kind for event in tied_events] == [EVENT_SUBMIT, EVENT_RESOLVE]


def test_freeze_django_now_refuses_after_cutoff():
    with pytest.raises(KonohaDatasetReplayError, match="cut-off"):
        freeze_django_now(OCCURRED_AT_MAX + timedelta(seconds=1))
    instant = parse_corpus_datetime("2025-08-06T16:20:00+02:00")
    with freeze_django_now(instant):
        assert timezone.now() == instant


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_remap_ishiraku_and_yakinuku_use_instance_routing_keys():
    organization = Organization.objects.create(name=ORGANIZATION_NAME)
    anbu = Establishment.objects.create(
        name=ESTABLISHMENT_ANBU,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    ishiraku = create_business_unit(
        establishment=anbu,
        key="restaurant",
        label=POLE_ISHIRAKU,
    )
    yakinuku = create_business_unit(
        establishment=anbu,
        key="restaurant",
        label=POLE_YAKINUKU,
    )
    assert ishiraku.routing_key != yakinuku.routing_key
    assert ishiraku.routing_key != "restaurant"
    runtime = ReplayRuntime(
        establishments={ESTABLISHMENT_ANBU: anbu},
        poles={
            (ESTABLISHMENT_ANBU, POLE_ISHIRAKU): ishiraku,
            (ESTABLISHMENT_ANBU, POLE_YAKINUKU): yakinuku,
        },
        memberships={},
        owners={},
    )
    candidate = {
        "title": "Rupture nori",
        "structured_summary": "Le nori manque au passage ramen.",
        "issue_focus": "rupture nori",
        "canonical_object": "nori",
        "signal_kind": "actionable",
        "expected_action": "replenish",
        "information_type": None,
        "affected_pole_specific_name": POLE_ISHIRAKU,
        "responsible_pole_specific_name": POLE_ISHIRAKU,
        "activity_subject_catalog_key": ishiraku.routing_key,
        "location_text": "Comptoir",
    }
    catalog_subject, _ = CatalogActivitySubject.objects.get_or_create(
        key="restaurant__stock",
        defaults={
            "catalog_business_unit": ishiraku.catalog_business_unit,
            "label": "Stock",
            "description": "",
            "active": True,
            "sort_order": 0,
        },
    )
    ActivitySubject.objects.create(
        establishment=anbu,
        business_unit=ishiraku,
        normalized_name=normalize_generic_activity_subject_name(catalog_subject.label),
        label="",
        routing_key="restaurant__stock",
        catalog_activity_subject=catalog_subject,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )
    ActivitySubject.objects.create(
        establishment=anbu,
        business_unit=yakinuku,
        normalized_name=normalize_generic_activity_subject_name(catalog_subject.label),
        label="",
        routing_key="restaurant__stock",
        catalog_activity_subject=catalog_subject,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
    )
    candidate["activity_subject_catalog_key"] = "restaurant__stock"
    ishiraku_out = remap_candidate_to_pipeline_output(
        candidate,
        establishment_name=ESTABLISHMENT_ANBU,
        runtime=runtime,
    )
    candidate["affected_pole_specific_name"] = POLE_YAKINUKU
    candidate["responsible_pole_specific_name"] = POLE_YAKINUKU
    yakinuku_out = remap_candidate_to_pipeline_output(
        candidate,
        establishment_name=ESTABLISHMENT_ANBU,
        runtime=runtime,
    )
    assert (
        ishiraku_out.candidates[0].affected_business_unit_routing_key == ishiraku.routing_key
    )
    assert (
        yakinuku_out.candidates[0].affected_business_unit_routing_key == yakinuku.routing_key
    )
    assert (
        ishiraku_out.candidates[0].activity_subject_routing_key == "restaurant__stock"
    )


def _build_mini_runtime(*, imported_catalog):
    del imported_catalog
    organization = Organization.objects.create(name=ORGANIZATION_NAME)
    anbu = Establishment.objects.create(
        name=ESTABLISHMENT_ANBU,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    akatsuki = Establishment.objects.create(
        name=ESTABLISHMENT_AKATSUKI,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    hotel = create_onboarding_business_unit(
        establishment=anbu,
        catalog_business_unit=CatalogBusinessUnit.objects.get(key="hotel"),
        specific_name=POLE_HOTEL,
        instance_description="Hôtel ANBU",
        generic_activity_subject_keys=["hotel__menage"],
    )
    maintenance = create_onboarding_business_unit(
        establishment=anbu,
        catalog_business_unit=CatalogBusinessUnit.objects.get(key="maintenance"),
        specific_name=POLE_MAINTENANCE,
        instance_description="Maintenance ANBU",
        generic_activity_subject_keys=["maintenance__cvc"],
    )
    naruto = _create_named_user(
        username=NARUTO_USERNAME,
        email=NARUTO_EMAIL,
        first_name="Naruto",
        last_name="Uzumaki",
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=anbu,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=akatsuki,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    authors = (
        ("anbu.hotel.staff1", "anbu.hotel.staff1@konoha.test", "Staff", "Hotel1"),
        ("anbu.hotel.mgr1", "anbu.hotel.mgr1@konoha.test", "Mgr", "Hotel1"),
        ("anbu.hotel.staff3", "anbu.hotel.staff3@konoha.test", "Staff", "Hotel3"),
    )
    for username, email, first_name, last_name in authors:
        _create_scoped_member(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            establishment=anbu,
            role=EstablishmentMembership.Role.STAFF,
            business_unit=hotel,
        )
    maintenance_actors = (
        (
            "anbu.maintenance.mgr1",
            "anbu.maintenance.mgr1@konoha.test",
            "Mgr",
            "Maint1",
            EstablishmentMembership.Role.MANAGER,
        ),
        (
            "anbu.maintenance.mgr2",
            "anbu.maintenance.mgr2@konoha.test",
            "Mgr",
            "Maint2",
            EstablishmentMembership.Role.MANAGER,
        ),
        (
            "anbu.maintenance.staff1",
            "anbu.maintenance.staff1@konoha.test",
            "Staff",
            "Maint1",
            EstablishmentMembership.Role.STAFF,
        ),
    )
    for username, email, first_name, last_name, role in maintenance_actors:
        _create_scoped_member(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            establishment=anbu,
            role=role,
            business_unit=maintenance,
        )
    return load_replay_runtime()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_mini_runtime_aggregates_then_opens_same_pattern(imported_catalog):
    coverage_before = list(
        AnalyticsHistoryCoverage.objects.values_list("reliable_from", flat=True)
    )
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    rows = _mini_corpus_rows()
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
        overrides={},
    )
    assert result.submitted == 3
    assert result.resolved == 1
    assert result.plans_created == 1
    assert result.plans_marked_done == 1
    assert result.plans_validated == 1
    first = Signal.objects.get(pk=result.signal_ids_by_group["anbu.hotel.sg.01"])
    second = Signal.objects.get(pk=result.signal_ids_by_group["anbu.hotel.sg.03"])
    assert first.id != second.id
    assert first.status == Signal.Status.RESOLVED
    assert second.status == Signal.Status.RESOLVED
    assert first.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN
    assert second.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_MANUAL
    assert first.resolved_at == parse_corpus_datetime("2025-08-08T18:00:00+02:00")
    assert second.resolved_at == parse_corpus_datetime("2025-08-19T11:00:00+02:00")

    for row in rows:
        observation = Observation.objects.get(raw_text=row["raw_text"])
        assert observation.submitted_at == parse_corpus_datetime(row["occurred_at"])
        candidate = observation.candidate_signals.get()
        if row["relation"] == "same_signal":
            assert candidate.outcome == CandidateSignal.Outcome.AGGREGATED_SIGNAL
            assert candidate.result_signal_id == first.id
        elif row["id"] == "anbu.hotel.01":
            assert candidate.outcome == CandidateSignal.Outcome.CREATED_SIGNAL
            assert candidate.result_signal_id == first.id
        else:
            assert candidate.outcome == CandidateSignal.Outcome.CREATED_SIGNAL
            assert candidate.result_signal_id == second.id

    first_pattern = SignalPatternAssignment.objects.get(signal=first).pattern_id
    second_pattern = SignalPatternAssignment.objects.get(signal=second).pattern_id
    assert first_pattern == second_pattern
    assert result.pattern_ids_by_group["anbu.hotel.pg.cvc"] == first_pattern
    first_pattern_row = SignalPatternAssignment.objects.get(signal=first).pattern
    assert first_pattern_row.label == "chambre 412 trop chaude"
    assert first_pattern_row.semantic_label == "chambre 412 trop chaude"
    assert Observation.objects.filter(establishment__name=ESTABLISHMENT_ANBU).count() == 3
    assert ActionPlan.objects.count() == 1
    execution = ActionPlanExecution.objects.get()
    assert execution.status == ActionPlanExecution.Status.DONE
    assert execution.source_signal_id == first.id
    assert execution.end_at == parse_corpus_datetime("2025-08-08T19:00:00+02:00")
    assert execution.task_executions.get().deadline_at == execution.end_at
    assert list(
        AnalyticsHistoryCoverage.objects.values_list("reliable_from", flat=True)
    ) == coverage_before


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_resume_skips_processed_and_refuses_orphan(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    rows = _mini_corpus_rows()
    first = replay_konoha_dataset_observations(
        dry_run=False,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
    )
    resumed = replay_konoha_dataset_observations(
        dry_run=False,
        resume=True,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
    )
    assert resumed.submitted == 0
    assert resumed.skipped >= 7
    assert Observation.objects.filter(establishment__name=ESTABLISHMENT_ANBU).count() == 3
    assert first.signal_ids_by_group == resumed.signal_ids_by_group

    Observation.objects.all().delete()
    membership = runtime.memberships[(ESTABLISHMENT_ANBU, rows[0]["author_email"])]
    orphan = Observation.objects.create(
        establishment=runtime.establishments[ESTABLISHMENT_ANBU],
        submitted_by_membership=membership,
        raw_text=rows[0]["raw_text"],
        submitted_at=parse_corpus_datetime(rows[0]["occurred_at"]),
    )
    ObservationProcessing.objects.create(
        observation=orphan,
        status=ObservationProcessing.Status.FAILED,
        queued_at=parse_corpus_datetime(rows[0]["occurred_at"]),
    )
    with pytest.raises(KonohaDatasetReplayError, match="not PROCESSED"):
        replay_konoha_dataset_observations(
            dry_run=False,
            resume=True,
            observations=rows[:1],
            runtime=runtime,
            skip_corpus_validation=True,
        )


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_command_requires_dry_run_or_confirm():
    stdout = StringIO()
    with pytest.raises(CommandError, match="--confirm"):
        call_command("replay_konoha_dataset_observations", stdout=stdout)
    assert not Observation.objects.exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_dry_run_prints_timeline_without_writes(imported_catalog):
    _build_mini_runtime(imported_catalog=imported_catalog)
    result = replay_konoha_dataset_observations(
        dry_run=True,
        observations=_mini_corpus_rows(),
        skip_corpus_validation=True,
        overrides={},
    )
    assert result.dry_run is True
    assert result.submitted == 0
    assert len(result.events) == 7
    assert not Observation.objects.exists()
    assert not Signal.objects.exists()


def _seed_later_season(establishment, *, month_start=date(2026, 8, 1)):
    if not GamificationSeason.objects.filter(
        establishment=establishment,
        status=GamificationSeason.Status.ACTIVE,
    ).exists():
        return open_season(establishment, month_start_local=month_start)
    occurred = parse_corpus_datetime("2026-08-15T12:00:00+02:00")
    starts, ends = month_bounds_for_occurred_at(
        establishment=establishment,
        occurred_at=occurred,
    )
    return GamificationSeason.objects.create(
        establishment=establishment,
        starts_at=starts,
        ends_at=ends,
        timezone=establishment.timezone,
        status=GamificationSeason.Status.CLOSED,
        closed_at=starts,
    )


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_replay_wipes_later_season_and_resolves(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    anbu = runtime.establishments[ESTABLISHMENT_ANBU]
    later = open_season(anbu, month_start_local=date(2026, 8, 1))
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=_mini_corpus_rows(),
        runtime=runtime,
        skip_corpus_validation=True,
    )
    assert result.submitted == 3
    assert result.resolved == 1
    assert not GamificationSeason.objects.filter(pk=later.pk).exists()
    first = Signal.objects.get(pk=result.signal_ids_by_group["anbu.hotel.sg.01"])
    assert first.resolved_at == parse_corpus_datetime("2025-08-08T18:00:00+02:00")
    replay_starts, _ = month_bounds_for_occurred_at(
        establishment=anbu,
        occurred_at=first.resolved_at,
    )
    assert GamificationSeason.objects.filter(
        establishment=anbu,
        starts_at=replay_starts,
    ).exists()
    assert PointTransaction.objects.filter(establishment=anbu).exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_replay_leaves_other_establishment_season(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    other = create_establishment(name="Other Hotel", timezone="Europe/Paris")
    other_season = open_season(other, month_start_local=date(2026, 8, 1))
    open_season(runtime.establishments[ESTABLISHMENT_ANBU], month_start_local=date(2026, 8, 1))
    replay_konoha_dataset_observations(
        dry_run=False,
        observations=_mini_corpus_rows(),
        runtime=runtime,
        skip_corpus_validation=True,
    )
    assert GamificationSeason.objects.filter(pk=other_season.pk).exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_dry_run_does_not_wipe_later_season(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    later = open_season(
        runtime.establishments[ESTABLISHMENT_ANBU],
        month_start_local=date(2026, 8, 1),
    )
    result = replay_konoha_dataset_observations(
        dry_run=True,
        observations=_mini_corpus_rows(),
        runtime=runtime,
        skip_corpus_validation=True,
    )
    assert result.submitted == 0
    assert GamificationSeason.objects.filter(pk=later.pk).exists()
    assert not Observation.objects.exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_resume_fails_fast_when_later_season_blocks_remaining(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    anbu = runtime.establishments[ESTABLISHMENT_ANBU]
    rows = _mini_corpus_rows()
    first_cycle = [row for row in rows if row["id"] in ("anbu.hotel.01", "anbu.hotel.02")]
    replay_konoha_dataset_observations(
        dry_run=False,
        observations=first_cycle,
        runtime=runtime,
        skip_corpus_validation=True,
    )
    later = _seed_later_season(anbu)
    with pytest.raises(KonohaDatasetReplayError, match="resume blocked"):
        replay_konoha_dataset_observations(
            dry_run=False,
            resume=True,
            observations=rows,
            runtime=runtime,
            skip_corpus_validation=True,
        )
    assert GamificationSeason.objects.filter(pk=later.pk).exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_resume_continues_prefix_when_no_later_seasons(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    rows = _mini_corpus_rows()
    first_cycle = [row for row in rows if row["id"] in ("anbu.hotel.01", "anbu.hotel.02")]
    replay_konoha_dataset_observations(
        dry_run=False,
        observations=first_cycle,
        runtime=runtime,
        skip_corpus_validation=True,
    )
    resumed = replay_konoha_dataset_observations(
        dry_run=False,
        resume=True,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
    )
    assert resumed.resolved == 1
    second = Signal.objects.get(pk=resumed.signal_ids_by_group["anbu.hotel.sg.03"])
    assert second.status == Signal.Status.RESOLVED
    assert second.resolved_at == parse_corpus_datetime("2025-08-19T11:00:00+02:00")


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_resume_noop_when_no_remaining_resolves(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    anbu = runtime.establishments[ESTABLISHMENT_ANBU]
    rows = _mini_corpus_rows()
    replay_konoha_dataset_observations(
        dry_run=False,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
    )
    later = _seed_later_season(anbu)
    season_ids = set(
        GamificationSeason.objects.filter(establishment=anbu).values_list("id", flat=True)
    )
    tx_ids = set(PointTransaction.objects.filter(establishment=anbu).values_list("id", flat=True))
    resumed = replay_konoha_dataset_observations(
        dry_run=False,
        resume=True,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
    )
    assert resumed.resolved == 0
    assert GamificationSeason.objects.filter(pk=later.pk).exists()
    assert set(
        GamificationSeason.objects.filter(establishment=anbu).values_list("id", flat=True)
    ) == season_ids
    assert set(
        PointTransaction.objects.filter(establishment=anbu).values_list("id", flat=True)
    ) == tx_ids


def _open_linked_plan_row(
    *,
    corpus_id: str,
    signal_group: str,
    occurred_at: str,
    planned_action_at: str,
) -> dict:
    row = deepcopy(_mini_corpus_rows()[0])
    row["id"] = corpus_id
    row["occurred_at"] = occurred_at
    row["signal_group"] = signal_group
    row["pattern_group"] = f"{signal_group}.pg"
    row["relation"] = "new_signal"
    row["same_signal_of"] = None
    row["cycle"] = {
        "open_at_cutoff": True,
        "resolved_at": None,
        "planned_action_at": planned_action_at,
        "resolution": "linked_plan",
    }
    return row


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_open_scheduled_plan_does_not_promote_after_cutoff(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    row = _open_linked_plan_row(
        corpus_id="anbu.hotel.cutoff.scheduled",
        signal_group="anbu.hotel.sg.cutoff.scheduled",
        occurred_at="2026-08-20T10:00:00+02:00",
        planned_action_at="2026-10-05T09:00:00+02:00",
    )
    overrides = {
        row["signal_group"]: {
            "created_at": "2026-08-20T11:00:00+02:00",
            "start_at": "2026-10-05T09:00:00+02:00",
            "end_at": "2026-10-05T17:00:00+02:00",
            "cutoff_execution_status": "scheduled",
        }
    }
    events = build_replay_events([row], overrides=overrides)
    assert [event.kind for event in events] == [EVENT_SUBMIT, EVENT_PLAN_CREATE]
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=[row],
        runtime=runtime,
        skip_corpus_validation=True,
        overrides=overrides,
    )
    execution = ActionPlanExecution.objects.get(
        pk=result.execution_ids_by_group[row["signal_group"]]
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[row["signal_group"]])
    assert execution.status == ActionPlanExecution.Status.SCHEDULED
    assert execution.marked_done_at is None
    assert signal.status == Signal.Status.IN_PROGRESS
    assert execution.start_at == parse_corpus_datetime("2026-10-05T09:00:00+02:00")


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_open_in_progress_overlay_promotes_before_cutoff(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    row = _open_linked_plan_row(
        corpus_id="anbu.hotel.cutoff.inprog",
        signal_group="anbu.hotel.sg.cutoff.inprog",
        occurred_at="2026-08-28T15:20:00+02:00",
        planned_action_at="2026-09-30T18:00:00+02:00",
    )
    overrides = {
        row["signal_group"]: {
            "created_at": "2026-08-28T16:00:00+02:00",
            "start_at": "2026-08-29T08:00:00+02:00",
            "end_at": "2026-09-30T18:00:00+02:00",
            "cutoff_execution_status": "in_progress",
        }
    }
    events = build_replay_events([row], overrides=overrides)
    assert [event.kind for event in events] == [
        EVENT_SUBMIT,
        EVENT_PLAN_CREATE,
        EVENT_PLAN_PROMOTE,
    ]
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=[row],
        runtime=runtime,
        skip_corpus_validation=True,
        overrides=overrides,
    )
    execution = ActionPlanExecution.objects.get(
        pk=result.execution_ids_by_group[row["signal_group"]]
    )
    assert execution.status == ActionPlanExecution.Status.IN_PROGRESS
    assert execution.marked_done_at is None
    assert execution.end_at == parse_corpus_datetime("2026-09-30T18:00:00+02:00")
    assert result.plans_promoted == 1


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_open_pending_validation_stops_before_validate(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    row = _open_linked_plan_row(
        corpus_id="anbu.hotel.cutoff.pending",
        signal_group="anbu.hotel.sg.cutoff.pending",
        occurred_at="2026-08-27T22:20:00+02:00",
        planned_action_at="2026-10-15T09:00:00+02:00",
    )
    overrides = {
        row["signal_group"]: {
            "requires_validation": True,
            "created_at": "2026-08-28T09:00:00+02:00",
            "marked_done_at": "2026-08-29T11:00:00+02:00",
            "end_at": "2026-10-15T09:00:00+02:00",
            "cutoff_execution_status": "pending_validation",
        }
    }
    events = build_replay_events([row], overrides=overrides)
    assert EVENT_PLAN_VALIDATE not in [event.kind for event in events]
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=[row],
        runtime=runtime,
        skip_corpus_validation=True,
        overrides=overrides,
    )
    execution = ActionPlanExecution.objects.get(
        pk=result.execution_ids_by_group[row["signal_group"]]
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[row["signal_group"]])
    assert execution.status == ActionPlanExecution.Status.PENDING_VALIDATION
    assert signal.status == Signal.Status.IN_PROGRESS
    assert result.plans_validated == 0


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_open_canceled_execution_reopens_signal(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    row = _open_linked_plan_row(
        corpus_id="anbu.hotel.cutoff.canceled",
        signal_group="anbu.hotel.sg.cutoff.canceled",
        occurred_at="2026-08-29T18:45:00+02:00",
        planned_action_at="2026-10-20T09:00:00+02:00",
    )
    overrides = {
        row["signal_group"]: {
            "created_at": "2026-08-29T19:15:00+02:00",
            "canceled_at": "2026-08-29T20:30:00+02:00",
            "cutoff_execution_status": "canceled",
        }
    }
    events = build_replay_events([row], overrides=overrides)
    assert [event.kind for event in events] == [
        EVENT_SUBMIT,
        EVENT_PLAN_CREATE,
        EVENT_PLAN_CANCEL,
    ]
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=[row],
        runtime=runtime,
        skip_corpus_validation=True,
        overrides=overrides,
    )
    execution = ActionPlanExecution.objects.get(
        pk=result.execution_ids_by_group[row["signal_group"]]
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[row["signal_group"]])
    assert execution.status == ActionPlanExecution.Status.CANCELED
    assert signal.status == Signal.Status.OPEN
    assert result.plans_canceled == 1


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_resume_skips_mark_done_by_fingerprint_not_status(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    rows = _mini_corpus_rows()
    first = replay_konoha_dataset_observations(
        dry_run=False,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
        overrides={},
    )
    execution = ActionPlanExecution.objects.get(
        source_signal_id=first.signal_ids_by_group["anbu.hotel.sg.01"]
    )
    marked_done_at = execution.marked_done_at
    resumed = replay_konoha_dataset_observations(
        dry_run=False,
        resume=True,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
        overrides={},
    )
    assert resumed.plans_marked_done == 0
    assert resumed.skipped >= 7
    ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    ).delete()
    execution.marked_done_at = None
    execution.save(update_fields=["marked_done_at", "updated_at"])
    with pytest.raises(KonohaDatasetReplayError, match="fingerprint diverges"):
        replay_konoha_dataset_observations(
            dry_run=False,
            resume=True,
            observations=rows,
            runtime=runtime,
            skip_corpus_validation=True,
            overrides={},
        )
    execution.marked_done_at = marked_done_at
    execution.save(update_fields=["marked_done_at", "updated_at"])


def _rows_for_groups(*groups: str) -> list[dict]:
    return [
        row
        for row in load_konoha_dataset_observations()
        if row["signal_group"] in groups
    ]


def test_interesting_timeline_has_no_plan_or_resolve():
    events = build_replay_events(_rows_for_groups("anbu.hotel.sg.05"), overrides={})
    assert [event.kind for event in events] == [EVENT_SUBMIT, EVENT_MARK_INTERESTING]


def test_rr_approve_timeline_has_no_manual_resolve():
    events = build_replay_events(_rows_for_groups("anbu.hotel.sg.21"), overrides={})
    assert [event.kind for event in events] == [
        EVENT_SUBMIT,
        EVENT_RR_CREATE,
        EVENT_RR_APPROVE,
    ]


def test_rr_reject_timeline_then_manual_resolve():
    events = build_replay_events(_rows_for_groups("anbu.ishiraku.sg.08"), overrides={})
    assert [event.kind for event in events] == [
        EVENT_SUBMIT,
        EVENT_RR_CREATE,
        EVENT_RR_REJECT,
        EVENT_RESOLVE,
    ]


def test_qualify_sorts_before_plan_create():
    events = build_replay_events(_rows_for_groups("anbu.maintenance.sg.05"), overrides={})
    kinds = [event.kind for event in events]
    assert EVENT_QUALIFY in kinds
    assert kinds.index(EVENT_QUALIFY) < kinds.index(EVENT_PLAN_CREATE)


@pytest.mark.django_db
def test_dry_run_full_corpus_counts_without_writes():
    events = build_replay_events(load_konoha_dataset_observations())
    counts = {kind: 0 for kind in (
        EVENT_SUBMIT,
        EVENT_QUALIFY,
        EVENT_RR_CREATE,
        EVENT_RR_APPROVE,
        EVENT_RR_REJECT,
        EVENT_MARK_INTERESTING,
        EVENT_PLAN_CREATE,
        EVENT_PLAN_PROMOTE,
        EVENT_PLAN_MARK_DONE,
        EVENT_PLAN_VALIDATE,
        EVENT_PLAN_CANCEL,
        EVENT_RESOLVE,
    )}
    for event in events:
        counts[event.kind] += 1
    assert counts[EVENT_SUBMIT] == 200
    assert counts[EVENT_QUALIFY] == 6
    assert counts[EVENT_RR_CREATE] == 4
    assert counts[EVENT_RR_APPROVE] == 3
    assert counts[EVENT_RR_REJECT] == 1
    assert counts[EVENT_MARK_INTERESTING] == 8
    assert counts[EVENT_PLAN_CREATE] == 106
    assert counts[EVENT_RESOLVE] == 65
    assert not Observation.objects.exists()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_remap_missing_subject_is_unassigned_ready():
    organization = Organization.objects.create(name=ORGANIZATION_NAME)
    anbu = Establishment.objects.create(
        name=ESTABLISHMENT_ANBU,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    coworking = create_business_unit(
        establishment=anbu,
        key="coworking",
        label="Coworking",
    )
    runtime = ReplayRuntime(
        establishments={ESTABLISHMENT_ANBU: anbu},
        poles={(ESTABLISHMENT_ANBU, "Coworking"): coworking},
        memberships={},
        owners={},
    )
    candidate = {
        "title": "Joint acoustique",
        "structured_summary": "Le joint d'isolation est decollé.",
        "issue_focus": "joint isolation decollé",
        "canonical_object": "joint acoustique",
        "signal_kind": "actionable",
        "expected_action": "repair",
        "information_type": None,
        "affected_pole_specific_name": "Coworking",
        "responsible_pole_specific_name": "Coworking",
        "activity_subject_catalog_key": None,
        "location_text": "Salle 2",
    }
    output = remap_candidate_to_pipeline_output(
        candidate,
        establishment_name=ESTABLISHMENT_ANBU,
        runtime=runtime,
    )
    assert output.candidates[0].activity_subject_routing_key is None


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_preflight_requires_kakashi_director_when_rr_uses_him(imported_catalog):
    runtime = _build_mini_runtime(imported_catalog=imported_catalog)
    from houston.establishments.konoha_dataset_replay import preflight_konoha_dataset_replay

    errors = preflight_konoha_dataset_replay(
        _rows_for_groups("anbu.communication.sg.02"),
        runtime=runtime,
        dry_run=True,
    )
    assert any("kakashi@konoha.com" in item for item in errors)


def _build_hotel_workflow_runtime(*, imported_catalog):
    del imported_catalog
    organization = Organization.objects.create(name=ORGANIZATION_NAME)
    anbu = Establishment.objects.create(
        name=ESTABLISHMENT_ANBU,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    akatsuki = Establishment.objects.create(
        name=ESTABLISHMENT_AKATSUKI,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    hotel = create_onboarding_business_unit(
        establishment=anbu,
        catalog_business_unit=CatalogBusinessUnit.objects.get(key="hotel"),
        specific_name=POLE_HOTEL,
        instance_description="Hôtel ANBU",
        generic_activity_subject_keys=["hotel__linge", "hotel__signaletique"],
    )
    naruto = _create_named_user(
        username=NARUTO_USERNAME,
        email=NARUTO_EMAIL,
        first_name="Naruto",
        last_name="Uzumaki",
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=anbu,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=akatsuki,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    actors = (
        (
            "anbu.hotel.staff1",
            "anbu.hotel.staff1@konoha.test",
            EstablishmentMembership.Role.STAFF,
        ),
        (
            "anbu.hotel.mgr1",
            "anbu.hotel.mgr1@konoha.test",
            EstablishmentMembership.Role.MANAGER,
        ),
        (
            "anbu.hotel.mgr2",
            "anbu.hotel.mgr2@konoha.test",
            EstablishmentMembership.Role.MANAGER,
        ),
    )
    for username, email, role in actors:
        _create_scoped_member(
            username=username,
            email=email,
            first_name=username,
            last_name="Hotel",
            establishment=anbu,
            role=role,
            business_unit=hotel,
        )
    return load_replay_runtime()


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_replay_marks_interesting_without_plan(imported_catalog):
    runtime = _build_hotel_workflow_runtime(imported_catalog=imported_catalog)
    rows = _rows_for_groups("anbu.hotel.sg.05")
    coverage_before = list(
        AnalyticsHistoryCoverage.objects.values_list("reliable_from", flat=True)
    )
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
        overrides={},
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group["anbu.hotel.sg.05"])
    assert signal.status == Signal.Status.INTERESTING
    assert result.marked_interesting == 1
    assert not ActionPlanExecution.objects.filter(source_signal=signal).exists()
    assert list(
        AnalyticsHistoryCoverage.objects.values_list("reliable_from", flat=True)
    ) == coverage_before


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_replay_rr_approve_has_no_manual_resolve_origin(imported_catalog):
    runtime = _build_hotel_workflow_runtime(imported_catalog=imported_catalog)
    rows = _rows_for_groups("anbu.hotel.sg.21")
    first = replay_konoha_dataset_observations(
        dry_run=False,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
        overrides={},
    )
    signal = Signal.objects.get(pk=first.signal_ids_by_group["anbu.hotel.sg.21"])
    assert signal.status == Signal.Status.RESOLVED
    assert signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST
    assert first.rr_approved == 1
    assert first.resolved == 0
    resumed = replay_konoha_dataset_observations(
        dry_run=False,
        resume=True,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
        overrides={},
    )
    assert resumed.rr_approved == 0
    assert resumed.skipped >= 3


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_resolve_fingerprint_conflicts_when_origin_is_resolution_request(
    imported_catalog,
):
    runtime = _build_hotel_workflow_runtime(imported_catalog=imported_catalog)
    rows = _rows_for_groups("anbu.hotel.sg.21")
    result = replay_konoha_dataset_observations(
        dry_run=False,
        observations=rows,
        runtime=runtime,
        skip_corpus_validation=True,
        overrides={},
    )

    event = ReplayEvent(
        kind=EVENT_RESOLVE,
        at=parse_corpus_datetime(rows[0]["cycle"]["resolved_at"]),
        corpus_id=rows[0]["id"],
        signal_group=rows[0]["signal_group"],
        pattern_group=rows[0]["pattern_group"],
        row=rows[0],
    )
    assert (
        _event_fingerprint(event, runtime=runtime, result=result) == FINGERPRINT_CONFLICT
    )


RR_REJECT_GROUP = "anbu.ishiraku.sg.08"


def _build_ishiraku_rr_runtime(*, imported_catalog):
    del imported_catalog
    organization = Organization.objects.create(name=ORGANIZATION_NAME)
    anbu = Establishment.objects.create(
        name=ESTABLISHMENT_ANBU,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    akatsuki = Establishment.objects.create(
        name=ESTABLISHMENT_AKATSUKI,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    ishiraku = create_onboarding_business_unit(
        establishment=anbu,
        catalog_business_unit=CatalogBusinessUnit.objects.get(key="restaurant"),
        specific_name=POLE_ISHIRAKU,
        instance_description="Ishiraku ANBU",
        generic_activity_subject_keys=["restaurant__mise_en_place"],
    )
    naruto = _create_named_user(
        username=NARUTO_USERNAME,
        email=NARUTO_EMAIL,
        first_name="Naruto",
        last_name="Uzumaki",
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=anbu,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=akatsuki,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    actors = (
        (
            "anbu.ishiraku.staff3",
            "anbu.ishiraku.staff3@konoha.test",
            EstablishmentMembership.Role.STAFF,
        ),
        (
            "anbu.ishiraku.mgr2",
            "anbu.ishiraku.mgr2@konoha.test",
            EstablishmentMembership.Role.MANAGER,
        ),
        (
            "ishiraku",
            "ishiraku@konoha.com",
            EstablishmentMembership.Role.MANAGER,
        ),
    )
    for username, email, role in actors:
        _create_scoped_member(
            username=username,
            email=email,
            first_name=username,
            last_name="Ishiraku",
            establishment=anbu,
            role=role,
            business_unit=ishiraku,
        )
    return load_replay_runtime()


def _replay_rr_reject_kinds(runtime, kinds: set[str]):
    rows = _rows_for_groups(RR_REJECT_GROUP)
    timeline = build_replay_events(rows, overrides={})
    events = [event for event in timeline if event.kind in kinds]
    result = ReplayResult(dry_run=False, resume=False, events=tuple(events))
    handlers = {
        EVENT_SUBMIT: _submit_event,
        EVENT_RR_CREATE: _rr_create_event,
        EVENT_RR_REJECT: _rr_reject_event,
        EVENT_RESOLVE: _resolve_event,
    }
    _wipe_konoha_gamification_state()
    with _suppress_replay_side_effects():
        for event in events:
            handlers[event.kind](event, runtime=runtime, result=result, resume=False)
    reject_event = next(event for event in timeline if event.kind == EVENT_RR_REJECT)
    return result, reject_event


def _rr_request(result) -> SignalResolutionRequest:
    signal_id = result.signal_ids_by_group[RR_REJECT_GROUP]
    return SignalResolutionRequest.objects.get(signal_id=signal_id)


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_rr_reject_fingerprint_match_while_signal_still_open(imported_catalog):
    runtime = _build_ishiraku_rr_runtime(imported_catalog=imported_catalog)
    result, event = _replay_rr_reject_kinds(
        runtime, {EVENT_SUBMIT, EVENT_RR_CREATE, EVENT_RR_REJECT}
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[RR_REJECT_GROUP])
    assert signal.status == Signal.Status.OPEN
    assert _event_fingerprint(event, runtime=runtime, result=result) == FINGERPRINT_MATCH


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_rr_reject_fingerprint_match_after_later_manual_resolve(imported_catalog):
    runtime = _build_ishiraku_rr_runtime(imported_catalog=imported_catalog)
    result, event = _replay_rr_reject_kinds(
        runtime,
        {EVENT_SUBMIT, EVENT_RR_CREATE, EVENT_RR_REJECT, EVENT_RESOLVE},
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[RR_REJECT_GROUP])
    assert signal.status == Signal.Status.RESOLVED
    assert signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_MANUAL
    assert _event_fingerprint(event, runtime=runtime, result=result) == FINGERPRINT_MATCH


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_rr_reject_fingerprint_conflicts_on_wrong_reviewer_reviewed_at_or_status(
    imported_catalog,
):
    runtime = _build_ishiraku_rr_runtime(imported_catalog=imported_catalog)
    result, event = _replay_rr_reject_kinds(
        runtime, {EVENT_SUBMIT, EVENT_RR_CREATE, EVENT_RR_REJECT}
    )
    request = _rr_request(result)
    reviewed_at = request.reviewed_at
    reviewer = request.reviewed_by_membership
    request.reviewed_by_membership = request.requested_by_membership
    request.save(update_fields=["reviewed_by_membership", "updated_at"])
    assert _event_fingerprint(event, runtime=runtime, result=result) == FINGERPRINT_CONFLICT
    request.reviewed_by_membership = reviewer
    request.reviewed_at = parse_corpus_datetime("2025-11-15T14:00:00+01:00")
    request.save(update_fields=["reviewed_by_membership", "reviewed_at", "updated_at"])
    assert _event_fingerprint(event, runtime=runtime, result=result) == FINGERPRINT_CONFLICT
    request.reviewed_at = reviewed_at
    request.status = SignalResolutionRequest.Status.APPROVED
    request.save(update_fields=["reviewed_at", "status", "updated_at"])
    assert _event_fingerprint(event, runtime=runtime, result=result) == FINGERPRINT_CONFLICT


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_rr_reject_fingerprint_conflicts_when_origin_is_resolution_request(
    imported_catalog,
):
    runtime = _build_ishiraku_rr_runtime(imported_catalog=imported_catalog)
    result, event = _replay_rr_reject_kinds(
        runtime,
        {EVENT_SUBMIT, EVENT_RR_CREATE, EVENT_RR_REJECT, EVENT_RESOLVE},
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[RR_REJECT_GROUP])
    signal.resolution_origin = SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST
    signal.save(update_fields=["resolution_origin", "updated_at"])
    assert _event_fingerprint(event, runtime=runtime, result=result) == FINGERPRINT_CONFLICT


QUALIFY_INCOMPLETE_GROUP = "anbu.maintenance.sg.05"
QUALIFY_RESOLVED_INCORRECT_GROUP = "akatsuki.commerce.sg.08"


def _build_qualify_fingerprint_runtime(*, imported_catalog):
    del imported_catalog
    organization = Organization.objects.create(name=ORGANIZATION_NAME)
    anbu = Establishment.objects.create(
        name=ESTABLISHMENT_ANBU,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    akatsuki = Establishment.objects.create(
        name=ESTABLISHMENT_AKATSUKI,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    maintenance = create_onboarding_business_unit(
        establishment=anbu,
        catalog_business_unit=CatalogBusinessUnit.objects.get(key="maintenance"),
        specific_name=POLE_MAINTENANCE,
        instance_description="Maintenance ANBU",
        generic_activity_subject_keys=["maintenance__prestataires_sous_traitance"],
    )
    commerce = create_onboarding_business_unit(
        establishment=akatsuki,
        catalog_business_unit=CatalogBusinessUnit.objects.get(key="commerce"),
        specific_name=POLE_COMMERCE,
        instance_description="Commerce AKATSUKI",
        generic_activity_subject_keys=["commerce__stock"],
    )
    akatsuki_maintenance = create_onboarding_business_unit(
        establishment=akatsuki,
        catalog_business_unit=CatalogBusinessUnit.objects.get(key="maintenance"),
        specific_name=POLE_MAINTENANCE,
        instance_description="Maintenance AKATSUKI",
        generic_activity_subject_keys=["maintenance__maintenance_batiment_second_uvre"],
    )
    naruto = _create_named_user(
        username=NARUTO_USERNAME,
        email=NARUTO_EMAIL,
        first_name="Naruto",
        last_name="Uzumaki",
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=anbu,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    EstablishmentMembership.objects.create(
        user=naruto,
        establishment=akatsuki,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    actors = (
        (
            "anbu.maintenance.mgr1",
            "anbu.maintenance.mgr1@konoha.test",
            EstablishmentMembership.Role.MANAGER,
            anbu,
            maintenance,
        ),
        (
            "akatsuki.commerce.staff3",
            "akatsuki.commerce.staff3@konoha.test",
            EstablishmentMembership.Role.STAFF,
            akatsuki,
            commerce,
        ),
        (
            "akatsuki.commerce.mgr1",
            "akatsuki.commerce.mgr1@konoha.test",
            EstablishmentMembership.Role.MANAGER,
            akatsuki,
            commerce,
        ),
        (
            "akatsuki.maintenance.staff1",
            "akatsuki.maintenance.staff1@konoha.test",
            EstablishmentMembership.Role.STAFF,
            akatsuki,
            akatsuki_maintenance,
        ),
    )
    for username, email, role, establishment, business_unit in actors:
        _create_scoped_member(
            username=username,
            email=email,
            first_name=username,
            last_name="Qualify",
            establishment=establishment,
            role=role,
            business_unit=business_unit,
        )
    return load_replay_runtime()


def _replay_qualify_kinds(runtime, group: str, kinds: set[str]):
    rows = _rows_for_groups(group)
    timeline = build_replay_events(rows, overrides={})
    events = [event for event in timeline if event.kind in kinds]
    result = ReplayResult(dry_run=False, resume=False, events=tuple(events))
    handlers = {EVENT_SUBMIT: _submit_event, EVENT_QUALIFY: _qualify_event}
    _wipe_konoha_gamification_state()
    with _suppress_replay_side_effects():
        for event in events:
            handlers[event.kind](event, runtime=runtime, result=result, resume=False)
    qualify_event = next(event for event in timeline if event.kind == EVENT_QUALIFY)
    return result, qualify_event


def _qualify_fingerprint(runtime, result, event) -> str:
    return _event_fingerprint(event, runtime=runtime, result=result)


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_qualify_fingerprint_missing_when_initial_is_unassigned(imported_catalog):
    runtime = _build_qualify_fingerprint_runtime(imported_catalog=imported_catalog)
    result, event = _replay_qualify_kinds(
        runtime, QUALIFY_INCOMPLETE_GROUP, {EVENT_SUBMIT}
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[QUALIFY_INCOMPLETE_GROUP])
    assert signal.routing_status == Signal.RoutingStatus.UNASSIGNED
    assert _qualify_fingerprint(runtime, result, event) == FINGERPRINT_MISSING


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_qualify_fingerprint_missing_when_initial_is_resolved_incorrect(
    imported_catalog,
):
    runtime = _build_qualify_fingerprint_runtime(imported_catalog=imported_catalog)
    result, event = _replay_qualify_kinds(
        runtime, QUALIFY_RESOLVED_INCORRECT_GROUP, {EVENT_SUBMIT}
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[QUALIFY_RESOLVED_INCORRECT_GROUP])
    assert signal.routing_status == Signal.RoutingStatus.RESOLVED
    assert _qualify_fingerprint(runtime, result, event) == FINGERPRINT_MISSING


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_qualify_fingerprint_match_after_writer(imported_catalog):
    runtime = _build_qualify_fingerprint_runtime(imported_catalog=imported_catalog)
    result, event = _replay_qualify_kinds(
        runtime, QUALIFY_INCOMPLETE_GROUP, {EVENT_SUBMIT, EVENT_QUALIFY}
    )
    assert result.qualified == 1
    assert _qualify_fingerprint(runtime, result, event) == FINGERPRINT_MATCH


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_qualify_fingerprint_match_after_last_activity_mutation(imported_catalog):
    runtime = _build_qualify_fingerprint_runtime(imported_catalog=imported_catalog)
    result, event = _replay_qualify_kinds(
        runtime, QUALIFY_INCOMPLETE_GROUP, {EVENT_SUBMIT, EVENT_QUALIFY}
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[QUALIFY_INCOMPLETE_GROUP])
    signal.last_activity_at = parse_corpus_datetime("2026-01-01T12:00:00+01:00")
    signal.save(update_fields=["last_activity_at", "updated_at"])
    assert _qualify_fingerprint(runtime, result, event) == FINGERPRINT_MATCH


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_qualify_fingerprint_conflict_without_manual_qualification_audit(
    imported_catalog,
):
    runtime = _build_qualify_fingerprint_runtime(imported_catalog=imported_catalog)
    result, event = _replay_qualify_kinds(
        runtime, QUALIFY_INCOMPLETE_GROUP, {EVENT_SUBMIT, EVENT_QUALIFY}
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[QUALIFY_INCOMPLETE_GROUP])
    for row in CandidateSignal.objects.filter(result_signal=signal):
        audit = dict(row.resolution_audit or {})
        audit["qualification_events"] = []
        row.resolution_audit = audit
        row.save(update_fields=["resolution_audit", "updated_at"])
    assert _qualify_fingerprint(runtime, result, event) == FINGERPRINT_CONFLICT


@override_settings(DEBUG=True, DATABASES=LOCAL_DATABASES)
def test_qualify_fingerprint_conflict_when_audit_resolved_key_diverges(
    imported_catalog,
):
    runtime = _build_qualify_fingerprint_runtime(imported_catalog=imported_catalog)
    result, event = _replay_qualify_kinds(
        runtime, QUALIFY_INCOMPLETE_GROUP, {EVENT_SUBMIT, EVENT_QUALIFY}
    )
    signal = Signal.objects.get(pk=result.signal_ids_by_group[QUALIFY_INCOMPLETE_GROUP])
    for row in CandidateSignal.objects.filter(result_signal=signal):
        audit = dict(row.resolution_audit or {})
        events = list(audit.get("qualification_events") or [])
        patched = []
        for envelope in events:
            item = dict(envelope)
            nested = dict(item.get("resolution_audit") or {})
            affected = dict(nested.get("affected") or {})
            affected["resolved_key"] = "other-routing-key"
            nested["affected"] = affected
            item["resolution_audit"] = nested
            patched.append(item)
        audit["qualification_events"] = patched
        row.resolution_audit = audit
        row.save(update_fields=["resolution_audit", "updated_at"])
    assert _qualify_fingerprint(runtime, result, event) == FINGERPRINT_CONFLICT
