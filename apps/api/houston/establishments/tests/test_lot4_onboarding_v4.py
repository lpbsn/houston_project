from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import IntegrityError

from houston.core.exceptions import DomainConflictError
from houston.establishments.business_unit_domain_service import (
    _create_business_unit_core,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogBusinessUnit,
    OnboardingProposal,
)
from houston.establishments.services import (
    PROPOSAL_SCHEMA_VERSION_V4_BU,
    OnboardingProposalValidationError,
    apply_onboarding_proposal,
    create_manual_onboarding_proposal,
    submit_manual_onboarding_proposal,
    validate_onboarding_proposal_payload,
)
from houston.testing.factories import create_user
from houston.testing.onboarding import create_onboarding_session

pytestmark = pytest.mark.django_db


def _v4_payload(*, business_units=None, activity_subjects=None) -> dict:
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION_V4_BU,
        "business_units": business_units
        or [
            {
                "client_key": "bu-coworking",
                "catalog_key": "coworking",
                "specific_name": "Coworking",
                "instance_description": "",
            }
        ],
        "activity_subjects": activity_subjects
        or [
            {
                "client_key": "subject-proprete",
                "business_unit_client_key": "bu-coworking",
                "catalog_key": "coworking__proprete",
            }
        ],
    }


def _validated_proposal(*, payload: dict):
    owner = create_user(username=f"lot4_owner_{uuid.uuid4().hex[:8]}")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=payload,
    )
    proposal = submit_manual_onboarding_proposal(proposal=proposal, actor=owner)
    return owner, session, proposal


def _error_codes(payload: dict) -> set[str]:
    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        validate_onboarding_proposal_payload(payload)
    return {error["code"] for error in exc_info.value.errors}


def test_v4_validation_canonicalizes_complete_payload_before_writes(imported_catalog):
    payload = _v4_payload(
        business_units=[
            {
                "client_key": "  bu-restaurant  ",
                "catalog_key": "  restaurant  ",
                "specific_name": "  Rooftop  ",
                "instance_description": "  Terrasse  ",
            }
        ],
        activity_subjects=[
            {
                "client_key": "  subject-stock  ",
                "business_unit_client_key": "  bu-restaurant  ",
                "catalog_key": "  restaurant__stock  ",
            },
            {
                "client_key": "  subject-free  ",
                "business_unit_client_key": "  bu-restaurant  ",
                "label": "  Terrasse VIP  ",
                "description": "  Privée  ",
            },
        ],
    )

    sanitized = validate_onboarding_proposal_payload(payload)

    assert sanitized == {
        "schema_version": PROPOSAL_SCHEMA_VERSION_V4_BU,
        "business_units": [
            {
                "client_key": "bu-restaurant",
                "catalog_key": "restaurant",
                "specific_name": "Rooftop",
                "instance_description": "Terrasse",
            }
        ],
        "activity_subjects": [
            {
                "client_key": "subject-stock",
                "business_unit_client_key": "bu-restaurant",
                "catalog_key": "restaurant__stock",
            },
            {
                "client_key": "subject-free",
                "business_unit_client_key": "bu-restaurant",
                "catalog_key": None,
                "label": "Terrasse VIP",
                "description": "Privée",
            },
        ],
    }
    assert not BusinessUnit.objects.exists()
    assert not ActivitySubject.objects.exists()


@pytest.mark.parametrize(
    ("payload", "expected_code"),
    [
        (
            _v4_payload(
                activity_subjects=[
                    {
                        "client_key": "subject",
                        "business_unit_client_key": "bu-coworking",
                    }
                ]
            ),
            "activity_subject_catalog_key_or_label_required",
        ),
        (
            _v4_payload(
                activity_subjects=[
                    {
                        "client_key": "subject",
                        "business_unit_client_key": "bu-coworking",
                        "catalog_key": "coworking__proprete",
                        "label": "Propreté",
                    }
                ]
            ),
            "activity_subject_catalog_key_or_label_required",
        ),
        (
            _v4_payload(
                activity_subjects=[
                    {
                        "client_key": "subject",
                        "business_unit_client_key": "missing-bu",
                        "label": "Libre",
                    }
                ]
            ),
            "orphan_activity_subject",
        ),
        (
            _v4_payload(
                activity_subjects=[
                    {
                        "client_key": "bu-coworking",
                        "business_unit_client_key": "bu-coworking",
                        "label": "Libre",
                    }
                ]
            ),
            "duplicate_client_key",
        ),
        (
            _v4_payload(
                activity_subjects=[
                    {
                        "client_key": "subject",
                        "business_unit_client_key": "bu-coworking",
                        "catalog_key": "hotel__menage",
                    }
                ]
            ),
            "catalog_subject_business_unit_mismatch",
        ),
        (
            _v4_payload(
                business_units=[
                    {
                        "client_key": "bu-restaurant",
                        "catalog_key": "restaurant",
                        "specific_name": "Rooftop",
                        "instance_description": "",
                    }
                ],
                activity_subjects=[
                    {
                        "client_key": "subject-stock",
                        "business_unit_client_key": "bu-restaurant",
                        "catalog_key": "restaurant__stock",
                    },
                    {
                        "client_key": "subject-free-stock",
                        "business_unit_client_key": "bu-restaurant",
                        "label": "Stock",
                    },
                ],
            ),
            "duplicate_activity_subject",
        ),
        (
            _v4_payload(
                business_units=[
                    {
                        "client_key": "bu-maintenance-a",
                        "catalog_key": "maintenance",
                        "specific_name": "Maintenance Nord",
                        "instance_description": "",
                    },
                    {
                        "client_key": "bu-maintenance-b",
                        "catalog_key": "maintenance",
                        "specific_name": "Maintenance Sud",
                        "instance_description": "",
                    },
                ],
                activity_subjects=[
                    {
                        "client_key": "subject-cvc",
                        "business_unit_client_key": "bu-maintenance-a",
                        "catalog_key": "maintenance__cvc",
                    },
                    {
                        "client_key": "subject-elec",
                        "business_unit_client_key": "bu-maintenance-b",
                        "catalog_key": "maintenance__electricite",
                    },
                ],
            ),
            "duplicate_transversal_catalog_instance",
        ),
    ],
)
def test_v4_validation_enforces_subject_identity_guards(
    imported_catalog,
    payload,
    expected_code,
):
    assert expected_code in _error_codes(payload)


def test_v4_submit_rejects_catalog_free_subject_normalized_name_collision(
    imported_catalog,
):
    owner = create_user(username=f"lot4_owner_{uuid.uuid4().hex[:8]}")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=_v4_payload(),
    )
    colliding_payload = _v4_payload(
        business_units=[
            {
                "client_key": "bu-restaurant",
                "catalog_key": "restaurant",
                "specific_name": "Rooftop",
                "instance_description": "",
            }
        ],
        activity_subjects=[
            {
                "client_key": "subject-stock",
                "business_unit_client_key": "bu-restaurant",
                "catalog_key": "restaurant__stock",
            },
            {
                "client_key": "subject-free-stock",
                "business_unit_client_key": "bu-restaurant",
                "label": "Stock",
            },
        ],
    )
    OnboardingProposal.objects.filter(id=proposal.id).update(payload=colliding_payload)
    proposal.refresh_from_db()

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        submit_manual_onboarding_proposal(proposal=proposal, actor=owner)

    assert any(
        error.get("code") == "duplicate_activity_subject" for error in exc_info.value.errors
    )
    proposal.refresh_from_db()
    assert proposal.status != OnboardingProposal.Status.VALIDATED


def test_v4_submit_rejects_duplicate_transversal_catalog_instance(imported_catalog):
    owner = create_user(username=f"lot4_owner_{uuid.uuid4().hex[:8]}")
    session = create_onboarding_session(actor=owner)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=_v4_payload(),
    )
    colliding_payload = _v4_payload(
        business_units=[
            {
                "client_key": "bu-maintenance-a",
                "catalog_key": "maintenance",
                "specific_name": "Maintenance Nord",
                "instance_description": "",
            },
            {
                "client_key": "bu-maintenance-b",
                "catalog_key": "maintenance",
                "specific_name": "Maintenance Sud",
                "instance_description": "",
            },
        ],
        activity_subjects=[
            {
                "client_key": "subject-cvc",
                "business_unit_client_key": "bu-maintenance-a",
                "catalog_key": "maintenance__cvc",
            },
            {
                "client_key": "subject-elec",
                "business_unit_client_key": "bu-maintenance-b",
                "catalog_key": "maintenance__electricite",
            },
        ],
    )
    OnboardingProposal.objects.filter(id=proposal.id).update(payload=colliding_payload)
    proposal.refresh_from_db()

    with pytest.raises(OnboardingProposalValidationError) as exc_info:
        submit_manual_onboarding_proposal(proposal=proposal, actor=owner)

    assert any(
        error.get("code") == "duplicate_transversal_catalog_instance"
        for error in exc_info.value.errors
    )
    proposal.refresh_from_db()
    assert proposal.status != OnboardingProposal.Status.VALIDATED


def test_v4_rejects_removed_v3_fields_and_unknown_schema(imported_catalog):
    payload = _v4_payload()
    payload["business_units"][0]["unit_type"] = "dedicated"
    payload["excluded_catalog_subject_keys"] = {}

    assert {"unknown_field", "unknown_section"} <= _error_codes(payload)
    assert "unsupported_schema_version" in _error_codes(
        {
            "schema_version": "onboarding_proposal_v5",
            "business_units": [],
            "activity_subjects": [],
        }
    )


def test_v4_apply_materializes_exact_payload_without_catalog_completion(imported_catalog):
    payload = _v4_payload(
        business_units=[
            {
                "client_key": "bu-restaurant",
                "catalog_key": "restaurant",
                "specific_name": "Rooftop",
                "instance_description": "Terrasse",
            }
        ],
        activity_subjects=[
            {
                "client_key": "subject-stock",
                "business_unit_client_key": "bu-restaurant",
                "catalog_key": "restaurant__stock",
            },
            {
                "client_key": "subject-free",
                "business_unit_client_key": "bu-restaurant",
                "label": "Terrasse VIP",
                "description": "Privée",
            },
        ],
    )
    owner, session, proposal = _validated_proposal(payload=payload)

    applied = apply_onboarding_proposal(proposal=proposal, actor=owner)

    business_unit = BusinessUnit.objects.get(establishment=session.establishment)
    subjects = ActivitySubject.objects.filter(business_unit=business_unit)
    assert applied.status == OnboardingProposal.Status.APPLIED
    assert business_unit.specific_name == "Rooftop"
    assert business_unit.instance_description == "Terrasse"
    assert business_unit.routing_key.startswith("restaurant--rooftop--")
    assert subjects.count() == 2
    assert set(subjects.values_list("routing_key", flat=True)) == {
        "restaurant__stock",
        subjects.get(catalog_activity_subject=None).routing_key,
    }
    assert subjects.get(routing_key="restaurant__stock").catalog_activity_subject_id
    assert subjects.get(catalog_activity_subject=None).label == "Terrasse VIP"


def test_v4_apply_never_reactivates_and_rolls_back_statuses(imported_catalog):
    owner = create_user(username=f"lot4_owner_{uuid.uuid4().hex[:8]}")
    session = create_onboarding_session(actor=owner)
    catalog = CatalogBusinessUnit.objects.get(key="coworking")
    inactive = _create_business_unit_core(
        establishment=session.establishment,
        catalog_business_unit=catalog,
        specific_name="Coworking",
    )
    BusinessUnit.objects.filter(id=inactive.id).update(active=False)
    proposal = create_manual_onboarding_proposal(
        session=session,
        actor=owner,
        payload=_v4_payload(),
    )
    proposal = submit_manual_onboarding_proposal(proposal=proposal, actor=owner)
    initial_proposal_status = proposal.status
    session.refresh_from_db()
    initial_session_status = session.status

    with pytest.raises(DomainConflictError) as exc_info:
        apply_onboarding_proposal(proposal=proposal, actor=owner)

    assert exc_info.value.code == "duplicate_specific_name"
    proposal.refresh_from_db()
    session.refresh_from_db()
    inactive.refresh_from_db()
    assert proposal.status == initial_proposal_status
    assert session.status == initial_session_status
    assert inactive.active is False
    assert BusinessUnit.objects.filter(establishment=session.establishment).count() == 1


def test_v4_apply_rolls_back_all_data_and_statuses_on_late_subject_failure(
    imported_catalog,
):
    payload = _v4_payload(
        business_units=[
            {
                "client_key": "bu-coworking",
                "catalog_key": "coworking",
                "specific_name": "Coworking",
                "instance_description": "",
            },
            {
                "client_key": "bu-restaurant",
                "catalog_key": "restaurant",
                "specific_name": "Rooftop",
                "instance_description": "",
            },
        ],
        activity_subjects=[
            {
                "client_key": "subject-proprete",
                "business_unit_client_key": "bu-coworking",
                "catalog_key": "coworking__proprete",
            },
            {
                "client_key": "subject-stock",
                "business_unit_client_key": "bu-restaurant",
                "catalog_key": "restaurant__stock",
            },
        ],
    )
    owner, session, proposal = _validated_proposal(payload=payload)
    initial_proposal_status = proposal.status
    session.refresh_from_db()
    initial_session_status = session.status
    original_bulk_create = ActivitySubject.objects.bulk_create
    bulk_create_calls = 0

    def fail_second_subject_insert(rows):
        nonlocal bulk_create_calls
        bulk_create_calls += 1
        if bulk_create_calls == 2:
            raise IntegrityError("forced late subject failure")
        return original_bulk_create(rows)

    with (
        patch(
            "houston.establishments.business_unit_domain_service."
            "ActivitySubject.objects.bulk_create",
            side_effect=fail_second_subject_insert,
        ),
        pytest.raises(DomainConflictError) as exc_info,
    ):
        apply_onboarding_proposal(proposal=proposal, actor=owner)

    assert exc_info.value.code == "activity_subject_identity_conflict"
    proposal.refresh_from_db()
    session.refresh_from_db()
    assert proposal.status == initial_proposal_status
    assert session.status == initial_session_status
    assert not BusinessUnit.objects.filter(establishment=session.establishment).exists()
    assert not ActivitySubject.objects.filter(establishment=session.establishment).exists()


def test_v4_apply_locks_proposal_then_session_then_establishment(imported_catalog):
    owner, _session, proposal = _validated_proposal(payload=_v4_payload())
    lock_order: list[str] = []

    from houston.establishments import services

    lock_proposal = services._lock_onboarding_proposal
    lock_session = services._lock_onboarding_session
    lock_establishment = services.Establishment.objects.select_for_update

    def record_proposal(value):
        lock_order.append("proposal")
        return lock_proposal(value)

    def record_session(value):
        lock_order.append("session")
        return lock_session(value)

    def record_establishment():
        lock_order.append("establishment")
        return lock_establishment()

    with (
        patch.object(services, "_lock_onboarding_proposal", side_effect=record_proposal),
        patch.object(services, "_lock_onboarding_session", side_effect=record_session),
        patch.object(
            services.Establishment.objects,
            "select_for_update",
            side_effect=record_establishment,
        ),
    ):
        apply_onboarding_proposal(proposal=proposal, actor=owner)

    assert lock_order[:3] == ["proposal", "session", "establishment"]
