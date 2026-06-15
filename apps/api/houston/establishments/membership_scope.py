from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q

from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.role_constants import _ADMIN_ROLES

if TYPE_CHECKING:
    from collections.abc import Iterable


class InvalidMembershipScopeAssignmentError(Exception):
    pass


class MembershipScopeType:
    BUSINESS_UNIT = "business_unit"


@dataclass(frozen=True)
class MembershipScopeInput:
    scope_type: str
    scope_id: UUID


@dataclass(frozen=True)
class ResolvedMembershipScope:
    business_unit: BusinessUnit


def membership_scope_prefetch() -> Prefetch:
    return Prefetch(
        "scope_links",
        queryset=MembershipScope.objects.select_related("business_unit"),
    )


def normalize_membership_scope_inputs(
    *,
    establishment: Establishment,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[ResolvedMembershipScope]:
    resolved = _resolve_scope_inputs(
        establishment=establishment,
        scope_inputs=scope_inputs,
    )
    return _dedupe_business_units(resolved)


@transaction.atomic
def replace_membership_scopes(
    *,
    membership: EstablishmentMembership,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[MembershipScope]:
    membership = EstablishmentMembership.objects.select_for_update().get(pk=membership.pk)
    establishment = membership.establishment
    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=scope_inputs,
    )

    requested_ids = {scope.business_unit.id for scope in normalized}

    existing_scopes = list(MembershipScope.objects.filter(membership=membership))
    for scope in existing_scopes:
        bu_id = _scope_business_unit_id(scope)
        if bu_id not in requested_ids:
            scope.delete()

    existing_bu_ids = {
        _scope_business_unit_id(scope)
        for scope in existing_scopes
        if _scope_business_unit_id(scope) in requested_ids
    }

    created: list[MembershipScope] = []
    for resolved in normalized:
        if resolved.business_unit.id in existing_bu_ids:
            continue
        try:
            with transaction.atomic():
                created.append(
                    MembershipScope.objects.create(
                        membership=membership,
                        business_unit=resolved.business_unit,
                    )
                )
        except IntegrityError:
            pass
        existing_bu_ids.add(resolved.business_unit.id)

    return created


def membership_scope_covers_business_unit(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> bool:
    for scope in _iter_membership_scopes(membership):
        bu_id = _scope_business_unit_id(scope)
        if bu_id == business_unit.id:
            return True
    return False


def membership_covers_business_unit_including_admins(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit | None,
) -> bool:
    """Whether an active member operationally covers a BusinessUnit.

    Owner/Director: implicit all-BU access within the establishment.
    Manager/Staff: explicit MembershipScope rows only.
    """
    if business_unit is None or not business_unit.active:
        return False
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return False
    if membership.establishment_id != business_unit.establishment_id:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role in {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }:
        return membership_scope_covers_business_unit(membership, business_unit)
    return False


def build_signal_feed_scope_q_v2(*, membership: EstablishmentMembership) -> Q | None:
    """Ma vue filter on affected OR responsible BusinessUnit scopes."""
    bu_ids: set[UUID] = set()
    for scope in _iter_membership_scopes(membership):
        bu_id = _scope_business_unit_id(scope)
        if bu_id is not None:
            bu_ids.add(bu_id)
    if not bu_ids:
        return None
    return Q(affected_business_unit_id__in=bu_ids) | Q(responsible_business_unit_id__in=bu_ids)


def build_action_visibility_scope_q(*, membership: EstablishmentMembership) -> Q | None:
    """Manager general feed: linked = affected OR responsible; free = responsible only."""
    bu_ids: set[UUID] = set()
    for scope in _iter_membership_scopes(membership):
        bu_id = _scope_business_unit_id(scope)
        if bu_id is not None:
            bu_ids.add(bu_id)
    if not bu_ids:
        return None
    linked_q = Q(signal_id__isnull=False) & (
        Q(affected_business_unit_id__in=bu_ids) | Q(responsible_business_unit_id__in=bu_ids)
    )
    free_q = Q(signal_id__isnull=True) & Q(responsible_business_unit_id__in=bu_ids)
    return linked_q | free_q


def _iter_membership_scopes(membership: EstablishmentMembership) -> Iterable[MembershipScope]:
    cache = getattr(membership, "_prefetched_objects_cache", None)
    if cache is not None and "scope_links" in cache:
        return membership.scope_links.all()

    return MembershipScope.objects.filter(membership=membership).select_related("business_unit")


def _resolve_scope_inputs(
    *,
    establishment: Establishment,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[ResolvedMembershipScope]:
    resolved_by_bu: dict[UUID, ResolvedMembershipScope] = {}

    for scope_input in scope_inputs:
        if scope_input.scope_type != MembershipScopeType.BUSINESS_UNIT:
            raise InvalidMembershipScopeAssignmentError("Scope type must be business_unit.")

        business_unit = _resolve_scope_input_to_business_unit(
            establishment=establishment,
            scope_input=scope_input,
        )
        resolved_by_bu[business_unit.id] = ResolvedMembershipScope(business_unit=business_unit)

    return list(resolved_by_bu.values())


def _resolve_scope_input_to_business_unit(
    *,
    establishment: Establishment,
    scope_input: MembershipScopeInput,
) -> BusinessUnit:
    business_unit = BusinessUnit.objects.filter(
        id=scope_input.scope_id,
        establishment=establishment,
        active=True,
    ).first()
    if business_unit is None:
        raise InvalidMembershipScopeAssignmentError(
            "Business unit scope must be active and belong to the same establishment."
        )
    return business_unit


def _dedupe_business_units(
    resolved_scopes: list[ResolvedMembershipScope],
) -> list[ResolvedMembershipScope]:
    seen: dict[UUID, ResolvedMembershipScope] = {}
    for scope in resolved_scopes:
        seen[scope.business_unit.id] = scope
    return list(seen.values())


def _scope_business_unit_id(scope: MembershipScope) -> UUID | None:
    return scope.business_unit_id


def parse_membership_scope_inputs(
    scopes: Iterable[dict[str, object]],
) -> list[MembershipScopeInput]:
    parsed: list[MembershipScopeInput] = []
    for item in scopes:
        if not isinstance(item, dict):
            raise InvalidMembershipScopeAssignmentError(
                "Each scope must include scope_type and scope_id."
            )
        scope_type = item.get("scope_type")
        scope_id = item.get("scope_id")
        if scope_type != MembershipScopeType.BUSINESS_UNIT:
            raise InvalidMembershipScopeAssignmentError("Scope type must be business_unit.")
        if scope_id is None:
            raise InvalidMembershipScopeAssignmentError("Each scope must include scope_id.")
        try:
            parsed_scope_id = UUID(str(scope_id))
        except (TypeError, ValueError) as exc:
            raise InvalidMembershipScopeAssignmentError(
                "Each scope must include a valid scope_id."
            ) from exc
        parsed.append(MembershipScopeInput(scope_type=scope_type, scope_id=parsed_scope_id))
    return parsed


def membership_scope_rows_for_membership(
    membership: EstablishmentMembership,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    business_unit_count = 0
    scopes_payload: list[dict[str, str]] = []
    seen_bu: set[UUID] = set()

    for scope in _iter_membership_scopes(membership):
        bu_id = _scope_business_unit_id(scope)
        if bu_id is None or bu_id in seen_bu:
            continue
        seen_bu.add(bu_id)
        scopes_payload.append(
            {
                "scope_type": MembershipScopeType.BUSINESS_UNIT,
                "scope_id": str(bu_id),
            }
        )
        business_unit_count += 1

    return scopes_payload, {
        "business_unit_count": business_unit_count,
    }


@transaction.atomic
def assign_membership_scopes(
    *,
    membership: EstablishmentMembership,
    scope_inputs: Iterable[MembershipScopeInput],
) -> None:
    replace_membership_scopes(membership=membership, scope_inputs=scope_inputs)


def scopes_not_allowed_for_role(role: str) -> bool:
    return role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }
