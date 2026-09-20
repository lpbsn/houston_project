from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.core.exceptions import DomainConflictError, DomainNotFoundError, DomainValidationError
from houston.establishments.business_unit_domain_service import create_onboarding_business_unit
from houston.establishments.catalog_import import sync_catalog_from_normalized_rows
from houston.establishments.membership_scope import InvalidMembershipScopeAssignmentError
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentMembership,
    OnboardingDraft,
    OnboardingSession,
)
from houston.establishments.services import (
    DirectorInvitationAlreadyExistsError,
    DirectorInvitationDuplicateError,
    DirectorInvitationOwnerNotAllowedError,
    EstablishmentAlreadyActiveError,
    InvalidDirectorInvitationInputError,
    InvalidMembershipInvitationInputError,
    InvalidOnboardingActivationStateError,
    MembershipInvitationOwnerConflictError,
    MembershipInvitationRoleNotAllowedError,
    MembershipInvitationUserExistsError,
    OnboardingDraftNotFoundError,
    OnboardingDraftValidationError,
    OnboardingReadinessError,
    OnboardingRuntimeAlreadyMaterializedError,
    OnboardingSessionTerminalError,
    OrganizationalOwnerInvariantConflictError,
    upsert_onboarding_draft_core,
)
from houston.platform.api.views import _denied_response
from houston.platform.exceptions import PlatformLifecycleDenied
from houston.platform.models import PlatformLifecycleEvent
from houston.platform.onboarding_services import (
    invite_platform_director,
    invite_platform_owner,
    map_onboarding_domain_error,
    start_platform_onboarding,
)
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_membership, create_user
from houston.testing.platform import grant_operator

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def _valid_payload(*, establishment_name: str, director_email: str) -> dict:
    bu_key = str(uuid.uuid4())
    subject_key = str(uuid.uuid4())
    return {
        "current_step": "team",
        "establishment": {
            "name": establishment_name,
            "description": "D" * ACTIVITY_DESCRIPTION_MIN_LENGTH,
        },
        "business_units": [
            {
                "client_key": bu_key,
                "catalog_key": "coworking",
                "specific_name": "Coworking Nord",
                "instance_description": "",
            }
        ],
        "activity_subjects": [
            {
                "client_key": subject_key,
                "business_unit_client_key": bu_key,
                "catalog_key": "coworking__proprete",
                "label": "",
                "description": "",
            }
        ],
        "team": {
            "director": {
                "email": director_email,
                "first_name": "Dir",
                "last_name": "Ector",
            },
            "members": [],
        },
    }


def _start_onboarding(api_client, token):
    created = api_client.post(
        "/api/v1/platform/onboardings/",
        {"organization_name": "Map Org", "establishment_name": "Map Site"},
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201
    return created.json()


def _operator_client(api_client, username: str):
    operator = create_user(username=username)
    grant_operator(operator)
    token = login(api_client, user=operator)
    return operator, token


def _assert_denied_event(*, action: str, resource_id, code: str) -> None:
    event = PlatformLifecycleEvent.objects.filter(
        action=action,
        resource_id=resource_id,
    ).latest("created_at")
    assert event.result == PlatformLifecycleEvent.Result.DENIED
    assert event.error_code == code


def _assert_failed_event(*, action: str, resource_id) -> None:
    event = PlatformLifecycleEvent.objects.filter(
        action=action,
        resource_id=resource_id,
    ).latest("created_at")
    assert event.result == PlatformLifecycleEvent.Result.FAILED
    assert event.error_code == "unexpected_error"


def test_denied_response_keeps_envelope_when_extra_clobbers_code_and_detail():
    exc = PlatformLifecycleDenied(
        "onboarding_draft_invalid",
        "Invalid draft.",
        extra={"code": "hijack", "detail": "nope", "errors": [{"code": "missing_director"}]},
    )
    response = _denied_response(exc)
    assert response.status_code == 400
    assert response.data["code"] == "onboarding_draft_invalid"
    assert response.data["detail"] == "Invalid draft."
    assert response.data["errors"] == [{"code": "missing_director"}]


def test_denied_response_ignores_none_extra():
    exc = PlatformLifecycleDenied("activation_not_ready")
    assert exc.extra is None
    response = _denied_response(exc)
    assert response.status_code == 409
    assert response.data == {"code": "activation_not_ready", "detail": "activation_not_ready"}


def test_start_platform_onboarding_blank_name_is_400():
    operator = create_user(username="plat_blank_org")
    grant_operator(operator)
    with pytest.raises(PlatformLifecycleDenied) as caught:
        start_platform_onboarding(operator=operator, organization_name="   ")
    assert caught.value.code == "invalid_organization_name"
    response = _denied_response(caught.value)
    assert response.status_code == 400
    assert response.data["code"] == "invalid_organization_name"


@pytest.mark.parametrize(
    ("exc", "code", "status_code"),
    [
        (
            OnboardingDraftValidationError([{"code": "missing_director"}]),
            "onboarding_draft_invalid",
            400,
        ),
        (
            InvalidDirectorInvitationInputError("A valid email is required."),
            "membership_invitation_invalid",
            400,
        ),
        (
            InvalidMembershipInvitationInputError("A valid email is required."),
            "membership_invitation_invalid",
            400,
        ),
        (InvalidMembershipScopeAssignmentError(), "membership_invitation_invalid", 400),
        (
            DomainValidationError("bad name", code="invalid_normalized_name"),
            "invalid_normalized_name",
            400,
        ),
        (
            DomainValidationError("mismatch", code="catalog_subject_business_unit_mismatch"),
            "catalog_subject_business_unit_mismatch",
            400,
        ),
        (DomainValidationError("fallback"), "validation_error", 400),
        (OnboardingDraftNotFoundError(), "draft_not_found", 404),
        (
            DomainNotFoundError("gone", code="business_unit_not_found"),
            "business_unit_not_found",
            404,
        ),
        (
            DomainNotFoundError("gone catalog", code="catalog_business_unit_not_found"),
            "catalog_business_unit_not_found",
            404,
        ),
        (OnboardingSessionTerminalError(), "invalid_onboarding_state", 409),
        (InvalidOnboardingActivationStateError("not draft"), "invalid_onboarding_state", 409),
        (
            OnboardingReadinessError(
                {"blockers": [{"code": "missing_active_owner_or_director"}]}
            ),
            "activation_not_ready",
            409,
        ),
        (EstablishmentAlreadyActiveError(), "establishment_already_active", 409),
        (OnboardingRuntimeAlreadyMaterializedError(), "runtime_already_materialized", 409),
        (DirectorInvitationAlreadyExistsError(), "director_invitation_already_exists", 409),
        (DirectorInvitationDuplicateError(), "membership_invitation_duplicate", 409),
        (MembershipInvitationUserExistsError(), "membership_invitation_user_exists", 409),
        (DirectorInvitationOwnerNotAllowedError(), "director_invitation_owner_not_allowed", 409),
        (MembershipInvitationOwnerConflictError(), "membership_invitation_owner_conflict", 409),
        (
            OrganizationalOwnerInvariantConflictError(),
            "organizational_owner_invariant_conflict",
            409,
        ),
        (
            DomainConflictError("inactive", code="catalog_business_unit_inactive"),
            "catalog_business_unit_inactive",
            409,
        ),
        (
            DomainConflictError("inactive subject", code="catalog_activity_subject_inactive"),
            "catalog_activity_subject_inactive",
            409,
        ),
        (
            DomainConflictError("dup", code="duplicate_specific_name"),
            "duplicate_specific_name",
            409,
        ),
        (
            DomainConflictError("dup t", code="duplicate_transversal_catalog_instance"),
            "duplicate_transversal_catalog_instance",
            409,
        ),
        (
            DomainConflictError("id", code="business_unit_identity_conflict"),
            "business_unit_identity_conflict",
            409,
        ),
        (
            DomainConflictError("n", code="duplicate_activity_subject_normalized_name"),
            "duplicate_activity_subject_normalized_name",
            409,
        ),
        (
            DomainConflictError("r", code="duplicate_activity_subject_routing_key"),
            "duplicate_activity_subject_routing_key",
            409,
        ),
        (
            DomainConflictError("a", code="activity_subject_identity_conflict"),
            "activity_subject_identity_conflict",
            409,
        ),
        (DomainConflictError("fallback"), "conflict_error", 409),
        (MembershipInvitationRoleNotAllowedError(), "membership_invitation_role_not_allowed", 403),
        (RuntimeError("boom"), None, None),
    ],
)
def test_map_onboarding_domain_error_codes_and_denied_status(exc, code, status_code):
    mapped = map_onboarding_domain_error(exc)
    if code is None:
        assert mapped is None
        return
    assert mapped is not None
    assert mapped.code == code
    if isinstance(exc, OnboardingDraftValidationError):
        assert mapped.extra == {"errors": exc.errors}
    response = _denied_response(mapped)
    assert response.status_code == status_code
    assert response.data["code"] == code


def test_http_complete_incomplete_draft_is_400(api_client):
    _operator, token = _operator_client(api_client, "plat_map_incomplete")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "onboarding_draft_invalid"
    assert isinstance(response.json()["errors"], list)
    assert response.json()["errors"]
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="onboarding_draft_invalid",
    )


def test_http_complete_missing_draft_is_404(api_client):
    _operator, token = _operator_client(api_client, "plat_map_missing_draft")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    OnboardingDraft.objects.filter(onboarding_session_id=session_id).delete()
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 404
    assert response.json()["code"] == "draft_not_found"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="draft_not_found",
    )


def test_http_complete_establishment_already_active_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_already_active")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    Establishment.objects.filter(pk=body["establishment_id"]).update(
        status=Establishment.Status.ACTIVE
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "establishment_already_active"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="establishment_already_active",
    )


def test_http_complete_terminal_session_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_terminal")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    OnboardingSession.objects.filter(pk=session_id).update(status=OnboardingSession.Status.CANCELED)
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_onboarding_state"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="invalid_onboarding_state",
    )


def test_http_complete_non_draft_establishment_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_non_draft")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    Establishment.objects.filter(pk=body["establishment_id"]).update(
        status=Establishment.Status.DEACTIVATED
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_onboarding_state"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="invalid_onboarding_state",
    )


def test_http_complete_runtime_already_materialized_is_409(api_client):
    sync_catalog_from_normalized_rows()
    operator, token = _operator_client(api_client, "plat_map_runtime")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    establishment = Establishment.objects.get(pk=body["establishment_id"])
    catalog = CatalogBusinessUnit.objects.get(key="coworking")
    create_onboarding_business_unit(
        establishment=establishment,
        catalog_business_unit=catalog,
        specific_name="Already There",
        generic_activity_subject_keys=["coworking__proprete"],
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "runtime_already_materialized"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="runtime_already_materialized",
    )


def test_http_complete_not_ready_is_409(api_client):
    sync_catalog_from_normalized_rows()
    operator, token = _operator_client(api_client, "plat_map_not_ready")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=f"dir_{uuid.uuid4().hex[:8]}@example.com",
        ),
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "activation_not_ready"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="activation_not_ready",
    )


def test_http_complete_director_slot_occupied_is_409(api_client):
    sync_catalog_from_normalized_rows()
    operator, token = _operator_client(api_client, "plat_map_dir_slot")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    occupant = create_user(username=f"dir_occ_{uuid.uuid4().hex[:8]}")
    create_membership(
        user=occupant,
        establishment=session.establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )
    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=f"other_{uuid.uuid4().hex[:8]}@example.com",
        ),
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/complete/",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "director_invitation_already_exists"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="director_invitation_already_exists",
    )


def test_http_complete_catalog_conflict_during_materialize_is_409(api_client):
    sync_catalog_from_normalized_rows()
    operator, token = _operator_client(api_client, "plat_map_catalog")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    session = OnboardingSession.objects.get(pk=session_id)
    upsert_onboarding_draft_core(
        session=session,
        actor=operator,
        payload=_valid_payload(
            establishment_name=session.establishment.name,
            director_email=f"dir_{uuid.uuid4().hex[:8]}@example.com",
        ),
    )
    with patch(
        "houston.establishments.services.create_onboarding_business_unit",
        side_effect=DomainConflictError(
            "Catalog business unit is inactive.",
            code="catalog_business_unit_inactive",
        ),
    ):
        response = api_client.post(
            f"/api/v1/platform/onboardings/{session_id}/complete/",
            **auth_headers(token),
        )
    assert response.status_code == 409
    assert response.json()["code"] == "catalog_business_unit_inactive"
    _assert_denied_event(
        action="complete_onboarding",
        resource_id=session_id,
        code="catalog_business_unit_inactive",
    )


def test_http_complete_unexpected_error_is_failed_500(api_client):
    _operator, token = _operator_client(api_client, "plat_map_failed")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    with patch(
        "houston.platform.onboarding_services.complete_onboarding_session_core",
        side_effect=RuntimeError("boom"),
    ):
        response = api_client.post(
            f"/api/v1/platform/onboardings/{session_id}/complete/",
            **auth_headers(token),
        )
    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    _assert_failed_event(action="complete_onboarding", resource_id=session_id)


def test_http_director_invite_terminal_session_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_dir_term")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    OnboardingSession.objects.filter(pk=session_id).update(status=OnboardingSession.Status.FAILED)
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
        {"email": "dir@example.com", "first_name": "Dir", "last_name": "Ector"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_onboarding_state"
    _assert_denied_event(
        action="invite_director",
        resource_id=session_id,
        code="invalid_onboarding_state",
    )


def test_http_director_invite_non_draft_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_dir_nd")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    Establishment.objects.filter(pk=body["establishment_id"]).update(
        status=Establishment.Status.DEACTIVATED
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
        {"email": "dir@example.com", "first_name": "Dir", "last_name": "Ector"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "invalid_onboarding_state"
    _assert_denied_event(
        action="invite_director",
        resource_id=session_id,
        code="invalid_onboarding_state",
    )


def test_http_director_invite_owner_email_not_allowed_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_dir_owner")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    establishment = Establishment.objects.get(pk=body["establishment_id"])
    owner = create_user(username=f"own_{uuid.uuid4().hex[:8]}")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
        {"email": owner.email, "first_name": "Dir", "last_name": "Ector"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "director_invitation_owner_not_allowed"
    _assert_denied_event(
        action="invite_director",
        resource_id=session_id,
        code="director_invitation_owner_not_allowed",
    )


def test_http_director_invite_slot_taken_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_dir_taken")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    establishment = Establishment.objects.get(pk=body["establishment_id"])
    occupant = create_user(username=f"dir_taken_{uuid.uuid4().hex[:8]}")
    create_membership(
        user=occupant,
        establishment=establishment,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.INVITED,
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
        {
            "email": f"other_{uuid.uuid4().hex[:8]}@example.com",
            "first_name": "Dir",
            "last_name": "Ector",
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "director_invitation_already_exists"
    _assert_denied_event(
        action="invite_director",
        resource_id=session_id,
        code="director_invitation_already_exists",
    )


def test_http_director_invite_duplicate_membership_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_dir_dup")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    establishment = Establishment.objects.get(pk=body["establishment_id"])
    staff = create_user(
        username=f"staff_{uuid.uuid4().hex[:8]}",
        status=User.Status.PENDING,
    )
    create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
        {"email": staff.email, "first_name": "Dir", "last_name": "Ector"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_duplicate"
    _assert_denied_event(
        action="invite_director",
        resource_id=session_id,
        code="membership_invitation_duplicate",
    )


def test_http_director_invite_user_exists_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_dir_exists")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    existing = create_user(username=f"exists_{uuid.uuid4().hex[:8]}")
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/director-invitations/",
        {"email": existing.email, "first_name": "Dir", "last_name": "Ector"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_user_exists"
    _assert_denied_event(
        action="invite_director",
        resource_id=session_id,
        code="membership_invitation_user_exists",
    )


def test_invite_platform_director_invalid_input_maps_without_http(api_client):
    operator, token = _operator_client(api_client, "plat_map_dir_invalid")
    body = _start_onboarding(api_client, token)
    session = OnboardingSession.objects.get(pk=body["id"])
    with pytest.raises(PlatformLifecycleDenied) as caught:
        invite_platform_director(
            operator=operator,
            session=session,
            email="   ",
            first_name="Dir",
            last_name="Ector",
        )
    assert caught.value.code == "membership_invitation_invalid"
    _assert_denied_event(
        action="invite_director",
        resource_id=session.id,
        code="membership_invitation_invalid",
    )


def test_http_owner_invite_non_owner_conflict_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_own_conflict")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    establishment = Establishment.objects.get(pk=body["establishment_id"])
    staff = create_user(username=f"own_staff_{uuid.uuid4().hex[:8]}")
    create_membership(
        user=staff,
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.INVITED,
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {"email": staff.email, "first_name": "Own", "last_name": "Er"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_owner_conflict"
    _assert_denied_event(
        action="invite_owner",
        resource_id=session_id,
        code="membership_invitation_owner_conflict",
    )


def test_http_owner_invite_active_sibling_owner_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_own_inv")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    establishment = Establishment.objects.get(pk=body["establishment_id"])
    sibling = Establishment.objects.create(
        name="Sibling Active",
        organization=establishment.organization,
        status=Establishment.Status.ACTIVE,
    )
    sibling_owner = create_user(
        username=f"sib_{uuid.uuid4().hex[:8]}",
        status=User.Status.PENDING,
    )
    create_membership(
        user=sibling_owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.INVITED,
    )
    create_membership(
        user=sibling_owner,
        establishment=sibling,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {"email": sibling_owner.email, "first_name": "Own", "last_name": "Er"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "organizational_owner_invariant_conflict"
    _assert_denied_event(
        action="invite_owner",
        resource_id=session_id,
        code="organizational_owner_invariant_conflict",
    )


def test_http_owner_invite_duplicate_active_owner_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_own_dup")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    establishment = Establishment.objects.get(pk=body["establishment_id"])
    owner = create_user(username=f"act_own_{uuid.uuid4().hex[:8]}")
    create_membership(
        user=owner,
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {"email": owner.email, "first_name": "Own", "last_name": "Er"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_duplicate"
    _assert_denied_event(
        action="invite_owner",
        resource_id=session_id,
        code="membership_invitation_duplicate",
    )


def test_http_owner_invite_user_exists_is_409(api_client):
    _operator, token = _operator_client(api_client, "plat_map_own_exists")
    body = _start_onboarding(api_client, token)
    session_id = body["id"]
    existing = create_user(username=f"own_exists_{uuid.uuid4().hex[:8]}")
    response = api_client.post(
        f"/api/v1/platform/onboardings/{session_id}/owner-invitations/",
        {"email": existing.email, "first_name": "Own", "last_name": "Er"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["code"] == "membership_invitation_user_exists"
    _assert_denied_event(
        action="invite_owner",
        resource_id=session_id,
        code="membership_invitation_user_exists",
    )


def test_invite_platform_owner_invalid_input_maps_without_http(api_client):
    operator, token = _operator_client(api_client, "plat_map_own_invalid")
    body = _start_onboarding(api_client, token)
    session = OnboardingSession.objects.get(pk=body["id"])
    with pytest.raises(PlatformLifecycleDenied) as caught:
        invite_platform_owner(
            operator=operator,
            session=session,
            email="   ",
            first_name="Own",
            last_name="Er",
        )
    assert caught.value.code == "membership_invitation_invalid"
    _assert_denied_event(
        action="invite_owner",
        resource_id=session.id,
        code="membership_invitation_invalid",
    )
