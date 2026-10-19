"""Deterministic contracts for the investigation engine. No provider call."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from houston.brain.comparability import (
    KpiMeasure,
    compare_measures,
    decompose_variation,
    measured_difference,
    measured_variation,
    recompose_amount,
    recompose_unit_price,
    recompose_volume,
    sum_values,
)
from houston.brain.contract import SCHEMA_VERSION
from houston.brain.investigation import (
    ENGINE_VERSION,
    QUALIFICATION_COMPLETE,
    QUALIFICATION_FACTUAL,
    QUALIFICATION_PARTIAL,
    QUALIFICATION_REFUSED,
    SIGNAL_TEXT_FIELDS,
    TREATMENT_CANCELED,
    TREATMENT_FAILED,
    InvestigationFacts,
    SubjectFinding,
    accept_deepening,
    authoritative_signal_text,
    copy_historical_signal,
    events_visible_at_capture,
    investigation_ceilings,
    investigation_engine,
    project_signal_copy,
    qualify,
)

CAPTURE_AT = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
MARCH = (date(2026, 3, 1), date(2026, 3, 8))
FEBRUARY = (date(2026, 2, 1), date(2026, 2, 8))


def kpi(**overrides) -> KpiMeasure:
    values = {
        "value": Decimal("100"),
        "unit": "EUR",
        "definition": "CA restauration",
        "scope": "restauration",
        "nature": "actual",
        "tax_treatment": "ht",
        "period_start": MARCH[0],
        "period_end": MARCH[1],
        "method": "tickets",
    }
    values.update(overrides)
    return KpiMeasure(**values)


def prior(**overrides) -> KpiMeasure:
    values = {"period_start": FEBRUARY[0], "period_end": FEBRUARY[1]}
    values.update(overrides)
    return kpi(**values)


def signal_payload(**extra) -> dict:
    payload = {
        "source_id": "signal-1",
        "recorded_at": "2026-03-02T08:00:00+00:00",
        "title": "Trois tables",
        "structured_summary": (
            "Au déjeuner, trois tables ont renoncé au dessert "
            "en raison d'une attente jugée trop longue."
        ),
        "location_text": "salle",
        "business_units": {"affected": {"id": "bu-1", "name": "restauration"}},
        "activity_subject": {"id": "act-1", "name": "dejeuner"},
        "operational_unit": {"id": "ou-1", "name": "salle"},
        "status_at_period_start": {"value": "open"},
        "status_at_period_end": {"value": "open"},
        "source_observation_link_counts": {
            "created_from": 1,
            "aggregated_from": 0,
            "merged_from": 0,
        },
        "mention": {
            "field": "structured_summary",
            "start": 0,
            "end": 12,
            "uncertainty": "text_mention",
        },
    }
    payload.update(extra)
    return payload


def test_two_periods_of_the_same_definition_are_comparable():
    verdict = compare_measures(kpi(), prior(), "temporal")

    assert verdict.accepted is True
    assert verdict.code == "accepted"
    assert verdict.reserve is None
    assert verdict.opening_days == (None, None)
    difference = measured_difference(
        kpi(value=Decimal("80")),
        prior(value=Decimal("100")),
        kind="temporal",
    )
    assert difference.accepted is True
    assert difference.value == Decimal("-20")
    assert difference.unit == "EUR"


def test_actual_against_budget_or_forecast_uses_the_same_period_and_scope():
    budget = compare_measures(
        kpi(),
        kpi(nature="budget", value=Decimal("80")),
        "actual_vs_reference",
    )
    forecast = compare_measures(
        kpi(),
        kpi(nature="forecast", value=Decimal("90")),
        "actual_vs_reference",
    )

    assert budget.accepted is True
    assert forecast.accepted is True
    difference = measured_difference(
        kpi(),
        kpi(nature="budget", value=Decimal("80")),
        kind="actual_vs_reference",
    )
    assert difference.value == Decimal("20")


def test_seven_days_against_five_requires_both_written_bases_and_is_not_rescaled():
    five_days = {"period_start": date(2026, 3, 1), "period_end": date(2026, 3, 6)}
    missing = compare_measures(kpi(), kpi(**five_days), "temporal")
    one_base = compare_measures(
        kpi(duration_days=7),
        kpi(**five_days, duration_days=None),
        "temporal",
    )
    both = compare_measures(
        kpi(duration_days=7, value=Decimal("700"), opening_days=None),
        kpi(**five_days, duration_days=5, value=Decimal("250"), opening_days=None),
        "temporal",
    )
    difference = measured_difference(
        kpi(duration_days=7, value=Decimal("700")),
        kpi(**five_days, duration_days=5, value=Decimal("250")),
        kind="temporal",
    )

    assert missing.code == "duration_base_missing"
    assert one_base.code == "duration_base_missing"
    assert both.accepted is True
    assert both.reserve == "unequal_duration_bases"
    assert both.duration_bases == (7, 5)
    assert both.opening_days == (None, None)
    assert difference.value == Decimal("450")


def test_tax_treatment_scope_definition_and_method_must_match():
    assert compare_measures(kpi(), prior(tax_treatment="ttc"), "temporal").code == "tax_mismatch"
    assert compare_measures(kpi(), prior(tax_treatment="ht"), "temporal").accepted is True
    assert (
        compare_measures(
            kpi(tax_treatment="unspecified"),
            prior(tax_treatment="ht"),
            "temporal",
        ).code
        == "tax_mismatch"
    )
    assert compare_measures(kpi(), prior(scope="hebergement"), "temporal").code == "scope_mismatch"
    assert (
        compare_measures(kpi(), prior(definition="couverts"), "temporal").code
        == "definition_mismatch"
    )
    assert compare_measures(kpi(), prior(method="caisse"), "temporal").code == "method_changed"
    assert compare_measures(kpi(method=None), prior(method=None), "temporal").accepted is True
    assert compare_measures(kpi(), prior(nature="budget"), "temporal").code == "nature_mixed"
    assert compare_measures(kpi(ambiguities=("ht_ttc",)), prior(), "temporal").code == "ambiguous"


def test_amount_identity_is_recomputed_and_a_missing_component_is_not_a_breakdown():
    identity = recompose_amount(
        volume=Decimal("100"),
        unit_price=Decimal("2.5"),
        published=Decimal("250"),
    )
    mismatch = recompose_amount(
        volume=Decimal("100"),
        unit_price=Decimal("2.5"),
        published=Decimal("249"),
    )
    unit_price = recompose_unit_price(amount=Decimal("250"), volume=Decimal("100"))
    volume = recompose_volume(amount=Decimal("250"), unit_price=Decimal("2.5"))
    missing_ratio = recompose_unit_price(amount=Decimal("250"), volume=None)
    missing_split = decompose_variation(
        volume_before=Decimal("100"),
        volume_after=Decimal("80"),
        price_before=Decimal("10"),
        price_after=None,
        amount_before=Decimal("1000"),
        amount_after=Decimal("800"),
    )
    split = decompose_variation(
        volume_before=Decimal("100"),
        volume_after=Decimal("80"),
        price_before=Decimal("10"),
        price_after=Decimal("10"),
        amount_before=Decimal("1000"),
        amount_after=Decimal("800"),
    )

    assert identity.accepted is True
    assert identity.value == Decimal("250")
    assert mismatch.accepted is False
    assert mismatch.code == "not_recomputed"
    assert mismatch.value is None
    assert unit_price.value == Decimal("2.5")
    assert volume.value == Decimal("100")
    assert missing_ratio.code == "component_missing"
    assert missing_ratio.value is None
    assert missing_split.accepted is False
    assert missing_split.code == "component_missing"
    assert missing_split.volume_effect is None
    assert missing_split.price_effect is None
    assert missing_split.amount_difference is None
    assert split.accepted is True
    assert split.volume_effect == Decimal("-200")
    assert split.price_effect == Decimal("0")
    assert split.amount_difference == Decimal("-200")


def test_rates_are_not_summed_or_varied_like_amounts():
    summed = sum_values((Decimal("10"), Decimal("5")), ("percent", "percent"))
    partial = sum_values((Decimal("10"), None), ("EUR", "EUR"))
    varied = measured_variation(
        kpi(unit="percent", value=Decimal("10")),
        prior(unit="percent", value=Decimal("12")),
    )
    differed = measured_difference(
        kpi(unit="percent", value=Decimal("10")),
        prior(unit="percent", value=Decimal("12")),
        kind="temporal",
    )

    assert summed.code == "rate_not_summable"
    assert summed.value is None
    assert partial.code == "component_missing"
    assert partial.value is None
    assert varied.code == "rate_variation"
    assert varied.value is None
    assert differed.accepted is True
    assert differed.value == Decimal("-2")
    assert differed.unit == "percent"


def test_reported_figures_alone_are_a_factual_reading():
    result = qualify(
        InvestigationFacts(
            subjects=(SubjectFinding(key="ca", examined=True, named=True),),
            reported_only=True,
        )
    )

    assert result.qualification == QUALIFICATION_FACTUAL
    assert result.investigation_succeeded is False
    assert result.qualification not in {QUALIFICATION_COMPLETE, QUALIFICATION_PARTIAL}


def test_an_accepted_decomposition_is_not_a_factual_reading():
    result = qualify(
        InvestigationFacts(
            subjects=(SubjectFinding(key="ca", examined=True, named=True),),
            reported_only=True,
            accepted_decomposition=True,
        )
    )

    assert result.qualification == QUALIFICATION_COMPLETE
    assert result.qualification != QUALIFICATION_FACTUAL
    assert result.investigation_succeeded is True


def test_examined_subjects_with_one_inconclusive_case_and_unread_candidates_are_complete():
    result = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(
                    key="drop",
                    examined=True,
                    verified_analytical=True,
                    cause_established=True,
                ),
                SubjectFinding(
                    key="rise",
                    examined=True,
                    verified_analytical=True,
                    cause_established=True,
                ),
                SubjectFinding(key="stable", examined=True, named=True),
            ),
            discovered_not_examined=("D-01", "D-02"),
        )
    )

    assert result.qualification == QUALIFICATION_COMPLETE
    assert result.investigation_succeeded is True
    assert result.blocked_finding_keys == ()


def test_an_unexamined_contradiction_blocks_the_finding_that_depends_on_it():
    blocked = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(
                    key="service",
                    examined=True,
                    affirmative=True,
                    verified_analytical=True,
                    cause_established=True,
                    unexamined_contradiction=True,
                ),
            ),
        )
    )
    remaining = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(
                    key="service",
                    examined=True,
                    affirmative=True,
                    verified_analytical=True,
                    cause_established=True,
                    unexamined_contradiction=True,
                ),
                SubjectFinding(
                    key="basket",
                    examined=True,
                    verified_analytical=True,
                    cause_established=True,
                ),
                SubjectFinding(key="open", examined=False, named=True),
            ),
        )
    )

    assert blocked.blocked_finding_keys == ("service",)
    assert blocked.qualification == QUALIFICATION_REFUSED
    assert blocked.investigation_succeeded is False
    assert remaining.qualification == QUALIFICATION_PARTIAL
    assert remaining.blocked_finding_keys == ("service",)
    assert "basket" not in remaining.blocked_finding_keys


def test_a_verified_decomposition_without_a_field_cause_can_be_partial():
    result = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(key="ca", examined=True, named=True),
                SubjectFinding(key="quality", examined=False, named=True),
            ),
            accepted_decomposition=True,
        )
    )

    assert result.qualification == QUALIFICATION_PARTIAL
    assert result.investigation_succeeded is True
    assert result.qualification != QUALIFICATION_FACTUAL


def test_an_excluded_competing_lead_blocks_an_exclusive_cause():
    exclusive = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(
                    key="service",
                    examined=True,
                    affirmative=True,
                    verified_analytical=True,
                    cause_established=True,
                ),
            ),
            competing_period_lead_excluded=True,
        )
    )
    decomposed = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(key="ca", examined=True, named=True),
                SubjectFinding(key="other", examined=False, named=True),
            ),
            accepted_decomposition=True,
            competing_period_lead_excluded=True,
        )
    )

    assert exclusive.qualification == QUALIFICATION_REFUSED
    assert exclusive.blocked_finding_keys == ("service",)
    assert exclusive.qualification != QUALIFICATION_COMPLETE
    assert decomposed.qualification == QUALIFICATION_PARTIAL
    assert decomposed.investigation_succeeded is True


def test_failed_or_canceled_treatment_is_not_a_partial_analysis():
    subjects = (
        SubjectFinding(
            key="ca",
            examined=True,
            verified_analytical=True,
            cause_established=True,
        ),
    )

    failed = qualify(InvestigationFacts(subjects=subjects, treatment=TREATMENT_FAILED))
    canceled = qualify(
        InvestigationFacts(
            subjects=subjects,
            accepted_decomposition=True,
            treatment=TREATMENT_CANCELED,
        )
    )

    assert failed.qualification is None
    assert failed.qualification != QUALIFICATION_PARTIAL
    assert failed.investigation_succeeded is False
    assert canceled.qualification is None
    assert canceled.investigation_succeeded is False


def test_a_gap_that_undermines_published_findings_is_refused():
    result = qualify(
        InvestigationFacts(
            subjects=(
                SubjectFinding(
                    key="ca",
                    examined=True,
                    verified_analytical=True,
                    cause_established=True,
                ),
                SubjectFinding(
                    key="gap",
                    examined=False,
                    named=True,
                    undermines_published=True,
                ),
            ),
            accepted_decomposition=True,
        )
    )

    assert result.qualification == QUALIFICATION_REFUSED
    assert result.investigation_succeeded is False


def test_signal_copy_keeps_title_and_structured_summary_only():
    clean, issues = project_signal_copy(signal_payload(), capture_at=CAPTURE_AT)
    dirty, dirty_issues = project_signal_copy(
        signal_payload(
            raw_text="OBSERVATION BRUTE",
            body="corps",
            comment="commentaire",
            transcription="transcription",
            description="description libre",
            observation={"body": "brut"},
            issue_focus="narration interne",
            expected_action="action attendue",
            status_at_capture={"value": "resolved"},
        ),
        capture_at=CAPTURE_AT,
    )
    nested, nested_issues = project_signal_copy(
        signal_payload(
            events=[
                {
                    "occurred_at": CAPTURE_AT,
                    "metadata": {"raw_text": "OBSERVATION BRUTE"},
                }
            ]
        ),
        capture_at=CAPTURE_AT,
    )

    assert issues == ()
    assert clean is not None
    assert authoritative_signal_text(clean) == {
        "title": "Trois tables",
        "structured_summary": signal_payload()["structured_summary"],
    }
    assert set(authoritative_signal_text(clean)) == set(SIGNAL_TEXT_FIELDS)
    assert "issue_focus" not in clean
    assert "raw_text" not in clean
    assert dirty is None
    assert "OBSERVATION BRUTE" not in " ".join(dirty_issues)
    assert "forbidden:raw_text" in dirty_issues
    assert "forbidden:description" in dirty_issues
    assert "disallowed:issue_focus" in dirty_issues
    assert "disallowed:status_at_capture" in dirty_issues
    assert nested is None
    assert "forbidden:raw_text" in nested_issues


def test_a_historical_signal_modified_after_capture_does_not_return_live_text():
    excluded = copy_historical_signal(
        created_at=CAPTURE_AT - timedelta(days=40),
        updated_at=CAPTURE_AT + timedelta(minutes=1),
        capture_at=CAPTURE_AT,
        payload=signal_payload(title="APRES", structured_summary="APRES"),
    )
    kept = copy_historical_signal(
        created_at=CAPTURE_AT - timedelta(days=40),
        updated_at=CAPTURE_AT,
        capture_at=CAPTURE_AT,
        payload=signal_payload(title="AVANT", structured_summary="AVANT"),
    )
    absent = copy_historical_signal(
        created_at=CAPTURE_AT + timedelta(seconds=1),
        updated_at=CAPTURE_AT + timedelta(seconds=1),
        capture_at=CAPTURE_AT,
        payload=signal_payload(title="APRES", structured_summary="APRES"),
    )

    assert excluded.payload is None
    assert excluded.exclusion == "modified_after_capture"
    assert excluded.issues == ()
    assert kept.payload is not None
    assert kept.payload["title"] == "AVANT"
    assert kept.payload["structured_summary"] == "AVANT"
    assert absent.payload is None
    assert absent.exclusion == "absent_at_capture"


def test_an_event_after_capture_is_not_historical_proof():
    earlier = {"occurred_at": CAPTURE_AT - timedelta(days=3), "event_type": "opened"}
    later = {"occurred_at": CAPTURE_AT + timedelta(days=2), "event_type": "resolved"}
    visible = events_visible_at_capture([earlier, later], CAPTURE_AT)
    rejected, issues = project_signal_copy(
        signal_payload(events=[earlier, later]),
        capture_at=CAPTURE_AT,
    )
    accepted, accepted_issues = project_signal_copy(
        signal_payload(events=list(visible)),
        capture_at=CAPTURE_AT,
    )

    assert visible == (earlier,)
    assert rejected is None
    assert "event_after_capture" in issues
    assert accepted_issues == ()
    assert accepted is not None
    assert accepted["events"] == [earlier]


def test_deepening_stays_inside_the_closed_menu_and_the_capture():
    same = "establishment-1"
    menu = accept_deepening(
        kind="seasonal_window",
        already_done=1,
        establishment_id=same,
        request_establishment_id=same,
    )
    outside = accept_deepening(
        kind="free_query",
        already_done=0,
        establishment_id=same,
        request_establishment_id=same,
    )
    exhausted = accept_deepening(
        kind="seasonal_window",
        already_done=2,
        establishment_id=same,
        request_establishment_id=same,
    )
    other = accept_deepening(
        kind="period_index_identifier",
        already_done=0,
        establishment_id=same,
        request_establishment_id="establishment-2",
    )
    late = accept_deepening(
        kind="completed_analysis_memory",
        already_done=0,
        establishment_id=same,
        request_establishment_id=same,
        target_at=CAPTURE_AT + timedelta(seconds=1),
        capture_at=CAPTURE_AT,
    )

    assert menu.accepted is True
    assert outside.code == "outside_menu"
    assert outside.accepted is False
    assert exhausted.code == "deepen_budget_exhausted"
    assert other.code == "outside_establishment"
    assert late.code == "after_capture"


def test_current_analyses_stay_on_the_existing_contract():
    ceilings = investigation_ceilings()

    assert SCHEMA_VERSION == "brain_analysis_v1"
    assert investigation_engine({"schema_version": SCHEMA_VERSION}) is False
    assert investigation_engine({}) is False
    assert investigation_engine({"engine_version": ENGINE_VERSION}) is True
    assert ceilings["per_call_input_tokens"] == 80_000
    assert ceilings["per_call_output_tokens"] == 8_000
    assert ceilings["provider_timeout_seconds"] == 180
    assert ceilings["max_semantic_readings"] == 3
    assert ceilings["max_provider_calls"] == 4
    assert ceilings["total_input_tokens"] == 320_000
