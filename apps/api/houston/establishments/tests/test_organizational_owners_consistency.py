from __future__ import annotations

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from houston.accounts.models import User
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.organizational_owners_consistency import (
    ISSUE_MISSING_FULL_COVERAGE_ACTIVE_OWNER,
    ISSUE_MISSING_OWNER,
    ISSUE_NON_OWNER_CONFLICT,
    ISSUE_OWNER_USER_STATUS_CONFLICT,
    ISSUE_STATUS_MIX,
    inventory_organizational_owners,
    repair_organizational_owners,
)
from houston.organizations.models import Organization
from houston.testing.factories import create_membership, create_user
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _org_with_two_establishments(
    *,
    est1_status: str = Establishment.Status.ACTIVE,
    est2_status: str = Establishment.Status.ACTIVE,
) -> tuple[Organization, Establishment, Establishment]:
    organization = Organization.objects.create(
        name="Org Owners Consistency",
        status=Organization.Status.ACTIVE,
    )
    est1 = Establishment.objects.create(
        name="Est One",
        organization=organization,
        status=est1_status,
    )
    est2 = Establishment.objects.create(
        name="Est Two",
        organization=organization,
        status=est2_status,
    )
    return organization, est1, est2


def _issue_codes(inventory, *, organization_id=None) -> set[str]:
    codes: set[str] = set()
    for report in inventory.organizations:
        if organization_id is not None and report.organization_id != organization_id:
            continue
        for issue in report.issues:
            codes.add(issue.code)
    return codes


def test_homogeneous_gap_dry_run_and_apply_creates_matching_status():
    organization, est1, est2 = _org_with_two_establishments()
    user = create_user(username="owner_gap")
    create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    dry = repair_organizational_owners(dry_run=True)
    assert len(dry.created) == 1
    assert dry.created[0].establishment_id == est2.id
    assert dry.created[0].status == EstablishmentMembership.Status.ACTIVE
    assert not EstablishmentMembership.objects.filter(
        user=user, establishment=est2
    ).exists()

    applied = repair_organizational_owners(dry_run=False)
    assert len(applied.created) == 1
    created = EstablishmentMembership.objects.get(user=user, establishment=est2)
    assert created.role == EstablishmentMembership.Role.OWNER
    assert created.status == EstablishmentMembership.Status.ACTIVE

    inventory = inventory_organizational_owners(organization_ids=[organization.id])
    assert ISSUE_MISSING_OWNER not in _issue_codes(inventory, organization_id=organization.id)
    assert not inventory.has_blocking_issues


def test_status_mix_preflight_and_repair_refuse():
    organization, est1, est2 = _org_with_two_establishments()
    user = create_user(username="owner_mix")
    create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        establishment=est2,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.INVITED,
    )

    inventory = inventory_organizational_owners(organization_ids=[organization.id])
    assert ISSUE_STATUS_MIX in _issue_codes(inventory, organization_id=organization.id)

    result = repair_organizational_owners(dry_run=False)
    assert result.created == []
    assert result.has_unresolved_conflicts
    assert EstablishmentMembership.objects.filter(user=user).count() == 2


def test_non_owner_conflict_blocks_promotion():
    organization, est1, est2 = _org_with_two_establishments()
    user = create_user(username="owner_non_owner")
    create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        establishment=est2,
        user=user,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    inventory = inventory_organizational_owners(organization_ids=[organization.id])
    assert ISSUE_NON_OWNER_CONFLICT in _issue_codes(
        inventory, organization_id=organization.id
    )

    before = list(
        EstablishmentMembership.objects.filter(user=user).values_list("id", "role", "status")
    )
    result = repair_organizational_owners(dry_run=False)
    assert result.created == []
    assert result.has_unresolved_conflicts
    after = list(
        EstablishmentMembership.objects.filter(user=user).values_list("id", "role", "status")
    )
    assert before == after


def test_preflight_fail_on_issues_exit_code():
    organization, est1, est2 = _org_with_two_establishments()
    user = create_user(username="owner_preflight_fail")
    create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    with pytest.raises(CommandError):
        call_command("preflight_organizational_owners", fail_on_issues=True)

    create_membership(
        establishment=est2,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    call_command("preflight_organizational_owners", fail_on_issues=True)


def test_org_atomicity_gap_plus_conflict_writes_nothing():
    organization, est1, est2 = _org_with_two_establishments()
    # Third establishment so one user can have a homogeneous gap while another conflicts.
    est3 = Establishment.objects.create(
        name="Est Three",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )

    conflict_user = create_user(username="owner_conflict_peer")
    create_membership(
        establishment=est1,
        user=conflict_user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        establishment=est2,
        user=conflict_user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.INVITED,
    )
    create_membership(
        establishment=est3,
        user=conflict_user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    gap_user = create_user(username="owner_gap_peer")
    create_membership(
        establishment=est1,
        user=gap_user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        establishment=est2,
        user=gap_user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    # gap_user missing on est3 — would be repairable alone, but org has status_mix.

    membership_count_before = EstablishmentMembership.objects.filter(
        establishment__organization=organization
    ).count()
    result = repair_organizational_owners(dry_run=False)
    assert result.created == []
    assert (
        EstablishmentMembership.objects.filter(establishment__organization=organization).count()
        == membership_count_before
    )
    assert not EstablishmentMembership.objects.filter(user=gap_user, establishment=est3).exists()


def test_multi_org_isolation_repairs_only_clean_org():
    clean_org, clean_est1, clean_est2 = _org_with_two_establishments()
    clean_user = create_user(username="owner_clean_org")
    create_membership(
        establishment=clean_est1,
        user=clean_user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    conflict_org, c_est1, c_est2 = _org_with_two_establishments()
    conflict_user = create_user(username="owner_conflict_org")
    create_membership(
        establishment=c_est1,
        user=conflict_user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        establishment=c_est2,
        user=conflict_user,
        role=EstablishmentMembership.Role.DIRECTOR,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    result = repair_organizational_owners(dry_run=False)
    assert EstablishmentMembership.objects.filter(
        user=clean_user, establishment=clean_est2
    ).exists()
    assert not EstablishmentMembership.objects.filter(
        user=conflict_user,
        establishment=c_est2,
        role=EstablishmentMembership.Role.OWNER,
    ).exists()
    assert any(plan.organization_id == clean_org.id for plan in result.created)
    assert conflict_org.id in result.skipped_organization_ids


def test_owner_user_status_conflict_blocks_repair_and_leaves_user():
    organization, est1, est2 = _org_with_two_establishments()
    user = create_user(username="owner_pending_conflict", status=User.Status.PENDING)
    create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership(
        establishment=est2,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    inventory = inventory_organizational_owners(organization_ids=[organization.id])
    assert ISSUE_OWNER_USER_STATUS_CONFLICT in _issue_codes(
        inventory, organization_id=organization.id
    )

    result = repair_organizational_owners(dry_run=False)
    assert result.created == []
    assert result.has_unresolved_conflicts
    user.refresh_from_db()
    assert user.status == User.Status.PENDING


def test_apply_is_idempotent():
    _organization, est1, est2 = _org_with_two_establishments()
    user = create_user(username="owner_idempotent")
    create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )

    first = repair_organizational_owners(dry_run=False)
    assert len(first.created) == 1
    second = repair_organizational_owners(dry_run=False)
    assert second.created == []
    assert (
        EstablishmentMembership.objects.filter(
            user=user,
            establishment__in=[est1, est2],
            role=EstablishmentMembership.Role.OWNER,
        ).count()
        == 2
    )


@pytest.mark.parametrize(
    "status",
    [
        EstablishmentMembership.Status.ACTIVE,
        EstablishmentMembership.Status.INVITED,
        EstablishmentMembership.Status.DEACTIVATED,
    ],
)
def test_repair_copies_homogeneous_status_exactly(status):
    organization, est1, est2 = _org_with_two_establishments(
        est1_status=Establishment.Status.DRAFT,
        est2_status=Establishment.Status.DRAFT,
    )
    user_status = (
        User.Status.PENDING
        if status == EstablishmentMembership.Status.INVITED
        else User.Status.ACTIVE
    )
    # deactivated owners on active users are fine; invited requires pending user.
    if status == EstablishmentMembership.Status.DEACTIVATED:
        user_status = User.Status.ACTIVE
    user = create_user(username=f"owner_status_{status}", status=user_status)
    create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=status,
    )

    result = repair_organizational_owners(dry_run=False)
    assert len(result.created) == 1
    created = EstablishmentMembership.objects.get(user=user, establishment=est2)
    assert created.status == status
    assert created.role == EstablishmentMembership.Role.OWNER

    inventory = inventory_organizational_owners(organization_ids=[organization.id])
    codes = _issue_codes(inventory, organization_id=organization.id)
    assert ISSUE_MISSING_OWNER not in codes
    # draft-only: missing full coverage is informative when status != active membership.
    full_coverage_issues = [
        issue
        for report in inventory.organizations
        if report.organization_id == organization.id
        for issue in report.issues
        if issue.code == ISSUE_MISSING_FULL_COVERAGE_ACTIVE_OWNER
    ]
    if status == EstablishmentMembership.Status.ACTIVE:
        assert full_coverage_issues == []
    else:
        assert full_coverage_issues
        assert all(not issue.blocking for issue in full_coverage_issues)


def test_repair_does_not_create_or_delete_scopes():
    organization, est1, est2 = _org_with_two_establishments()
    user = create_user(username="owner_scopes")
    owner_membership = create_membership(
        establishment=est1,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    # Existing scope on a staff membership must remain untouched; owners get no scopes.
    staff = create_user(username="staff_with_scope")
    staff_membership = create_membership(
        establishment=est1,
        user=staff,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    business_unit = create_business_unit(establishment=est1, key="kitchen", label="Kitchen")
    scope = create_membership_with_business_unit_scope(
        membership=staff_membership,
        business_unit=business_unit,
    )
    scope_ids_before = set(MembershipScope.objects.values_list("id", flat=True))

    repair_organizational_owners(dry_run=False)

    created_owner = EstablishmentMembership.objects.get(user=user, establishment=est2)
    assert not MembershipScope.objects.filter(membership=created_owner).exists()
    assert not MembershipScope.objects.filter(membership=owner_membership).exists()
    assert set(MembershipScope.objects.values_list("id", flat=True)) == scope_ids_before
    assert MembershipScope.objects.filter(id=scope.id).exists()
