from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import IntegrityError, close_old_connections, transaction

from houston.establishments.membership_scope import (
    InvalidMembershipScopeAssignmentError,
    MembershipScopeInput,
    MembershipScopeType,
    normalize_membership_scope_inputs,
    parse_membership_scope_inputs,
    replace_membership_scopes,
)
from houston.establishments.models import (
    MembershipScope,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
)

pytestmark = pytest.mark.django_db


def test_membership_scope_model_requires_exactly_one_target():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="hotel_scope_model")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MembershipScope.objects.create(membership=membership)

    scope = MembershipScope.objects.create(membership=membership, business_unit=business_unit)
    assert scope.scope_type == "business_unit"
    assert scope.scope_id == business_unit.id


def test_duplicate_scope_type_and_id_rejected():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="hotel_scope_dup")
    MembershipScope.objects.create(membership=membership, business_unit=business_unit)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MembershipScope.objects.create(membership=membership, business_unit=business_unit)


def test_normalize_dedupes_duplicate_business_unit_inputs():
    establishment = create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    assert len(normalized) == 1
    assert normalized[0].business_unit.id == business_unit.id


def test_normalize_dedupes_redundant_business_unit_scope_inputs():
    establishment = create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    assert len(normalized) == 1
    assert normalized[0].business_unit.key == "hotel"


def test_cross_establishment_business_unit_rejected():
    establishment_a = create_establishment(name="Hotel A")
    establishment_b = create_establishment(name="Hotel B")
    business_unit_a = create_business_unit(establishment=establishment_a, key="hotel")

    with pytest.raises(InvalidMembershipScopeAssignmentError):
        normalize_membership_scope_inputs(
            establishment=establishment_b,
            scope_inputs=[
                MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit_a.id)
            ],
        )


def test_inactive_business_unit_rejected():
    establishment = create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel")
    business_unit.active = False
    business_unit.save(update_fields=["active", "updated_at"])

    with pytest.raises(InvalidMembershipScopeAssignmentError):
        normalize_membership_scope_inputs(
            establishment=establishment,
            scope_inputs=[
                MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id)
            ],
        )


def test_parse_membership_scope_inputs_rejects_legacy_scope_types():
    with pytest.raises(InvalidMembershipScopeAssignmentError, match="business_unit"):
        parse_membership_scope_inputs(
            [{"scope_type": "domain", "scope_id": "00000000-0000-0000-0000-000000000001"}]
        )


def test_replace_membership_scopes_persists_business_unit_row():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    scopes = list(MembershipScope.objects.filter(membership=membership))
    assert len(scopes) == 1
    assert scopes[0].business_unit_id == business_unit.id


@pytest.mark.django_db(transaction=True)
def test_concurrent_replace_membership_scopes_same_business_unit_is_idempotent():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="concurrent_hotel")
    scope_input = MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id)

    def assign_scope(_: int) -> None:
        close_old_connections()
        try:
            replace_membership_scopes(
                membership=membership,
                scope_inputs=[scope_input],
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(assign_scope, range(2)))

    scopes = list(MembershipScope.objects.filter(membership=membership))
    assert len(scopes) == 1
    assert scopes[0].business_unit_id == business_unit.id


def test_replace_membership_scopes_reraises_unexpected_integrity_error(monkeypatch):
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="unexpected_integrity")

    def raise_integrity_error(**_kwargs):
        raise IntegrityError("unexpected constraint violation")

    monkeypatch.setattr(MembershipScope.objects, "create", raise_integrity_error)

    with pytest.raises(IntegrityError, match="unexpected constraint violation"):
        replace_membership_scopes(
            membership=membership,
            scope_inputs=[
                MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
            ],
        )

    assert MembershipScope.objects.filter(membership=membership).count() == 0
