from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction
from django.db.models import Prefetch, Q

from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)

if TYPE_CHECKING:
    from collections.abc import Iterable


class InvalidMembershipScopeAssignmentError(Exception):
    pass


class MembershipScopeType:
    MODULE = "module"
    DOMAIN = "domain"
    SUBJECT = "subject"

    _ALL = frozenset({MODULE, DOMAIN, SUBJECT})


@dataclass(frozen=True)
class MembershipScopeInput:
    scope_type: str
    scope_id: UUID


@dataclass(frozen=True)
class ResolvedMembershipScope:
    operational_module: OperationalModule | None = None
    operational_domain: OperationalDomain | None = None
    operational_subject: OperationalSubject | None = None

    @property
    def scope_type(self) -> str:
        if self.operational_module is not None:
            return MembershipScopeType.MODULE
        if self.operational_domain is not None:
            return MembershipScopeType.DOMAIN
        return MembershipScopeType.SUBJECT

    @property
    def scope_id(self) -> UUID:
        if self.operational_module is not None:
            return self.operational_module.id
        if self.operational_domain is not None:
            return self.operational_domain.id
        assert self.operational_subject is not None
        return self.operational_subject.id


def membership_scope_prefetch() -> Prefetch:
    return Prefetch(
        "scope_links",
        queryset=MembershipScope.objects.select_related(
            "operational_module",
            "operational_domain",
            "operational_domain__operational_module",
            "operational_subject",
            "operational_subject__operational_domain",
            "operational_subject__operational_domain__operational_module",
        ),
    )


def normalize_membership_scope_inputs(
    *,
    establishment: Establishment,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[ResolvedMembershipScope]:
    """Validate scope inputs and return normalized explicit scopes (no DB write)."""
    resolved = _resolve_scope_inputs(
        establishment=establishment,
        scope_inputs=scope_inputs,
    )
    return _normalize_resolved_scopes(resolved)


@transaction.atomic
def replace_membership_scopes(
    *,
    membership: EstablishmentMembership,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[MembershipScope]:
    """Replace all scope links for a membership with validated, normalized scopes."""
    establishment = membership.establishment
    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=scope_inputs,
    )

    requested_keys = {_resolved_scope_key(scope) for scope in normalized}

    existing_scopes = list(
        MembershipScope.objects.filter(membership=membership).select_related(
            "operational_module",
            "operational_domain",
            "operational_subject",
        )
    )
    for scope in existing_scopes:
        resolved = _membership_scope_to_resolved(scope)
        if _resolved_scope_key(resolved) not in requested_keys:
            scope.delete()

    existing_keys = {
        _resolved_scope_key(_membership_scope_to_resolved(scope)) for scope in existing_scopes
    }
    existing_keys &= requested_keys

    created: list[MembershipScope] = []
    for resolved in normalized:
        key = _resolved_scope_key(resolved)
        if key in existing_keys:
            continue
        created.append(
            MembershipScope.objects.create(
                membership=membership,
                operational_module=resolved.operational_module,
                operational_domain=resolved.operational_domain,
                operational_subject=resolved.operational_subject,
            )
        )
        existing_keys.add(key)

    return created


def membership_scope_covers_module(
    membership: EstablishmentMembership,
    module: OperationalModule,
) -> bool:
    for scope in _iter_membership_scopes(membership):
        if scope.operational_module_id == module.id:
            return True
    return False


def membership_scope_covers_domain(
    membership: EstablishmentMembership,
    domain: OperationalDomain,
) -> bool:
    for scope in _iter_membership_scopes(membership):
        if scope.operational_domain_id == domain.id:
            return True
        if scope.operational_module_id is not None and domain.operational_module_id is not None:
            if scope.operational_module_id == domain.operational_module_id:
                return True
    return False


def membership_scope_covers_subject(
    membership: EstablishmentMembership,
    subject: OperationalSubject,
) -> bool:
    subject_domain = subject.operational_domain
    for scope in _iter_membership_scopes(membership):
        if scope.operational_subject_id == subject.id:
            return True
        if scope.operational_domain_id is not None and subject_domain is not None:
            if scope.operational_domain_id == subject_domain.id:
                return True
        if (
            scope.operational_module_id is not None
            and subject_domain is not None
            and subject_domain.operational_module_id is not None
        ):
            if scope.operational_module_id == subject_domain.operational_module_id:
                return True
    return False


def build_signal_feed_scope_q(*, membership: EstablishmentMembership) -> Q | None:
    """
    Build a Signal feed filter from explicit MembershipScope rows (strict FK per row).

    Returns None when the membership has no scope links (personal feed must be empty).
    """
    conditions = Q()
    has_scope = False
    for scope in _iter_membership_scopes(membership):
        has_scope = True
        if scope.operational_module_id is not None:
            conditions |= Q(operational_module_id=scope.operational_module_id)
        elif scope.operational_domain_id is not None:
            conditions |= Q(operational_domain_id=scope.operational_domain_id)
        elif scope.operational_subject_id is not None:
            conditions |= Q(operational_subject_id=scope.operational_subject_id)
    if not has_scope:
        return None
    return conditions


def _iter_membership_scopes(membership: EstablishmentMembership) -> Iterable[MembershipScope]:
    cache = getattr(membership, "_prefetched_objects_cache", None)
    if cache is not None and "scope_links" in cache:
        return membership.scope_links.all()

    return MembershipScope.objects.filter(membership=membership).select_related(
        "operational_module",
        "operational_domain",
        "operational_domain__operational_module",
        "operational_subject",
        "operational_subject__operational_domain",
        "operational_subject__operational_domain__operational_module",
    )


def _resolve_scope_inputs(
    *,
    establishment: Establishment,
    scope_inputs: Iterable[MembershipScopeInput],
) -> list[ResolvedMembershipScope]:
    resolved_by_key: dict[tuple[str, UUID], ResolvedMembershipScope] = {}

    for scope_input in scope_inputs:
        if scope_input.scope_type not in MembershipScopeType._ALL:
            raise InvalidMembershipScopeAssignmentError(
                "Scope type must be module, domain, or subject."
            )

        resolved = _resolve_single_scope_input(
            establishment=establishment,
            scope_input=scope_input,
        )
        key = _resolved_scope_key(resolved)
        resolved_by_key[key] = resolved

    return list(resolved_by_key.values())


def _resolve_single_scope_input(
    *,
    establishment: Establishment,
    scope_input: MembershipScopeInput,
) -> ResolvedMembershipScope:
    if scope_input.scope_type == MembershipScopeType.MODULE:
        module = (
            OperationalModule.objects.filter(
                id=scope_input.scope_id,
                establishment=establishment,
                active=True,
            )
            .only("id", "establishment_id", "active")
            .first()
        )
        if module is None:
            raise InvalidMembershipScopeAssignmentError(
                "Operational scope must be active and belong to the same establishment."
            )
        return ResolvedMembershipScope(operational_module=module)

    if scope_input.scope_type == MembershipScopeType.DOMAIN:
        domain = (
            OperationalDomain.objects.filter(
                id=scope_input.scope_id,
                establishment=establishment,
                active=True,
            )
            .select_related("operational_module")
            .only(
                "id",
                "establishment_id",
                "active",
                "operational_module_id",
            )
            .first()
        )
        if domain is None:
            raise InvalidMembershipScopeAssignmentError(
                "Operational scope must be active and belong to the same establishment."
            )
        return ResolvedMembershipScope(operational_domain=domain)

    subject = (
        OperationalSubject.objects.filter(
            id=scope_input.scope_id,
            establishment=establishment,
            active=True,
        )
        .select_related("operational_domain", "operational_domain__operational_module")
        .only(
            "id",
            "establishment_id",
            "active",
            "operational_domain_id",
        )
        .first()
    )
    if subject is None:
        raise InvalidMembershipScopeAssignmentError(
            "Operational scope must be active and belong to the same establishment."
        )
    return ResolvedMembershipScope(operational_subject=subject)


def _normalize_resolved_scopes(
    resolved_scopes: list[ResolvedMembershipScope],
) -> list[ResolvedMembershipScope]:
    module_ids = {
        scope.operational_module.id
        for scope in resolved_scopes
        if scope.operational_module is not None
    }
    domain_ids = {
        scope.operational_domain.id
        for scope in resolved_scopes
        if scope.operational_domain is not None
    }

    normalized: list[ResolvedMembershipScope] = []
    for scope in resolved_scopes:
        if scope.operational_module is not None:
            normalized.append(scope)
            continue

        if scope.operational_domain is not None:
            domain = scope.operational_domain
            if (
                domain.operational_module_id is not None
                and domain.operational_module_id in module_ids
            ):
                continue
            normalized.append(scope)
            continue

        subject = scope.operational_subject
        assert subject is not None
        subject_domain = subject.operational_domain
        if subject_domain is not None:
            if subject_domain.id in domain_ids:
                continue
            if (
                subject_domain.operational_module_id is not None
                and subject_domain.operational_module_id in module_ids
            ):
                continue
        normalized.append(scope)

    return normalized


def _resolved_scope_key(resolved: ResolvedMembershipScope) -> tuple[str, UUID]:
    return (resolved.scope_type, resolved.scope_id)


def _membership_scope_to_resolved(scope: MembershipScope) -> ResolvedMembershipScope:
    return ResolvedMembershipScope(
        operational_module=scope.operational_module,
        operational_domain=scope.operational_domain,
        operational_subject=scope.operational_subject,
    )


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
        if not isinstance(scope_type, str) or scope_type not in MembershipScopeType._ALL:
            raise InvalidMembershipScopeAssignmentError(
                "Scope type must be module, domain, or subject."
            )
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
    module_count = 0
    domain_count = 0
    subject_count = 0
    scopes_payload: list[dict[str, str]] = []

    for scope in _iter_membership_scopes(membership):
        scopes_payload.append(
            {
                "scope_type": scope.scope_type,
                "scope_id": str(scope.scope_id),
            }
        )
        if scope.operational_module_id is not None:
            module_count += 1
        elif scope.operational_domain_id is not None:
            domain_count += 1
        else:
            subject_count += 1

    return scopes_payload, {
        "module_count": module_count,
        "domain_count": domain_count,
        "subject_count": subject_count,
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
