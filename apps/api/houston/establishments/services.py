from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from houston.accounts.models import UserSession
from houston.establishments.access import get_onboarding_access_context
from houston.establishments.models import (
    ACTIVITY_DESCRIPTION_MIN_LENGTH,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipDomain,
    OnboardingCatalogDomain,
    OnboardingCatalogModule,
    OnboardingCatalogUnit,
    OnboardingProposal,
    OnboardingSession,
    OperationalDomain,
    OperationalModule,
    OperationalUnit,
    RoutingHint,
    RoutingHintDomain,
    RuntimeTag,
    RuntimeTagDomain,
    RuntimeVocabulary,
)
from houston.establishments.selectors import (
    get_membership_for_management,
    get_runtime_config_for_session,
)
from houston.organizations.models import Organization


class MembershipManagementNotFoundError(Exception):
    pass


class InvalidMembershipDomainAssignmentError(Exception):
    pass


class CannotDeactivateLastActiveOwnerError(Exception):
    pass


class CannotDemoteLastActiveOwnerError(Exception):
    pass


class ActiveOnboardingSessionExistsError(Exception):
    pass


class InvalidOnboardingSessionScopeError(Exception):
    pass


class UnsupportedOnboardingSessionSourceModeError(Exception):
    pass


class OnboardingAccessDeniedError(Exception):
    pass


class OnboardingSessionTerminalError(Exception):
    pass


class InvalidActivityDescriptionError(Exception):
    pass


class OnboardingReadinessError(Exception):
    def __init__(self, readiness: dict):
        super().__init__("Onboarding session is not ready for activation.")
        self.readiness = readiness


class ActiveOnboardingProposalExistsError(Exception):
    pass


class OnboardingProposalValidationError(Exception):
    def __init__(self, errors: list[dict]):
        super().__init__("Onboarding proposal payload is invalid.")
        self.errors = errors


class OnboardingProposalStateError(Exception):
    pass


@dataclass(frozen=True)
class MembershipUpdateInput:
    role: str | None = None
    operational_domains: list[str] | None = None


PROPOSAL_SCHEMA_VERSION = "onboarding_proposal_v1"
PROPOSAL_REQUIRED_SECTIONS = frozenset(
    {
        "operational_modules",
        "operational_domains",
    }
)
PROPOSAL_OPTIONAL_SECTIONS = frozenset(
    {
        "operational_units",
        "runtime_vocabulary",
        "runtime_tags",
        "routing_hints",
    }
)
PROPOSAL_SECTIONS = PROPOSAL_REQUIRED_SECTIONS | PROPOSAL_OPTIONAL_SECTIONS
PROPOSAL_EXCLUDED_SECTIONS = frozenset(
    {
        "roles",
        "memberships",
        "billing",
        "subscription",
        "checklists",
        "checklist_templates",
        "signal_examples",
        "observations",
        "signals",
        "actions",
        "comments",
        "permissions",
    }
)
PROPOSAL_SECTION_CAPS = {
    "operational_modules": 10,
    "operational_domains": 15,
    "operational_units": 15,
    "runtime_vocabulary": 30,
    "runtime_tags": 30,
    "routing_hints": 30,
}
PROPOSAL_MAX_ROUTING_HINT_DOMAINS = 4
PROPOSAL_SECTION_ACCEPTED = "accepted"
PROPOSAL_SECTION_SKIPPED = "skipped"
PROPOSAL_SECTION_REJECTED = "rejected"
PROPOSAL_SECTION_DECISIONS = {
    PROPOSAL_SECTION_ACCEPTED,
    PROPOSAL_SECTION_SKIPPED,
    PROPOSAL_SECTION_REJECTED,
}


def validate_onboarding_proposal_payload(payload: dict) -> dict:
    errors: list[dict] = []

    if not isinstance(payload, dict):
        raise OnboardingProposalValidationError([_proposal_error("invalid_payload_type")])

    if payload.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
        errors.append(_proposal_error("unsupported_schema_version", field="schema_version"))

    for section in PROPOSAL_REQUIRED_SECTIONS:
        if section not in payload:
            errors.append(_proposal_error("missing_required_section", section=section))

    for section in payload:
        if section == "schema_version":
            continue
        if section in PROPOSAL_EXCLUDED_SECTIONS:
            errors.append(_proposal_error("excluded_section", section=section))
        elif section not in PROPOSAL_SECTIONS:
            errors.append(_proposal_error("unknown_section", section=section))

    sanitized = _empty_proposal_payload()
    catalogs = _active_onboarding_catalog_keys()

    raw_modules = _section_items(payload, "operational_modules", errors)
    raw_domains = _section_items(payload, "operational_domains", errors)
    raw_units = _section_items(payload, "operational_units", errors)
    raw_vocabulary = _section_items(payload, "runtime_vocabulary", errors)
    raw_tags = _section_items(payload, "runtime_tags", errors)
    raw_hints = _section_items(payload, "routing_hints", errors)

    modules = _validate_catalog_keyed_section(
        section="operational_modules",
        items=raw_modules,
        allowed_keys=catalogs["modules"],
        errors=errors,
    )
    module_keys = {item["key"] for item in modules}

    domains = _validate_catalog_keyed_section(
        section="operational_domains",
        items=raw_domains,
        allowed_keys=catalogs["domains"],
        errors=errors,
        related_module_keys=module_keys,
    )
    domain_keys = {item["key"] for item in domains}

    units = _validate_catalog_keyed_section(
        section="operational_units",
        items=raw_units,
        allowed_keys=catalogs["units"],
        errors=errors,
        related_module_keys=module_keys,
    )
    unit_keys = {item["key"] for item in units}

    sanitized["operational_modules"] = modules
    sanitized["operational_domains"] = domains
    sanitized["operational_units"] = units
    sanitized["runtime_vocabulary"] = _validate_vocabulary_section(
        raw_vocabulary,
        domain_keys=domain_keys,
        unit_keys=unit_keys,
        errors=errors,
    )
    sanitized["runtime_tags"] = _validate_runtime_tag_section(
        raw_tags,
        domain_keys=domain_keys,
        errors=errors,
    )
    sanitized["routing_hints"] = _validate_routing_hint_section(
        raw_hints,
        domain_keys=domain_keys,
        unit_keys=unit_keys,
        errors=errors,
    )

    if len(modules) < 1:
        errors.append(_proposal_error("insufficient_required_modules"))
    if len(domains) < 3:
        errors.append(_proposal_error("insufficient_required_domains"))

    if errors:
        raise OnboardingProposalValidationError(errors)

    return sanitized


@transaction.atomic
def create_manual_onboarding_proposal(
    *,
    session: OnboardingSession,
    actor,
    payload: dict,
) -> OnboardingProposal:
    return _create_onboarding_proposal(
        session=session,
        actor=actor,
        payload=payload,
        source=OnboardingProposal.Source.MANUAL,
    )


@transaction.atomic
def create_template_onboarding_proposal(
    *,
    session: OnboardingSession,
    actor,
    payload: dict,
) -> OnboardingProposal:
    return _create_onboarding_proposal(
        session=session,
        actor=actor,
        payload=payload,
        source=OnboardingProposal.Source.TEMPLATE,
    )


@transaction.atomic
def create_ai_onboarding_proposal(
    *,
    session: OnboardingSession,
    actor,
    payload: dict,
) -> OnboardingProposal:
    return _create_onboarding_proposal(
        session=session,
        actor=actor,
        payload=payload,
        source=OnboardingProposal.Source.AI_PROPOSED,
    )


@transaction.atomic
def validate_onboarding_proposal_section(
    *,
    proposal: OnboardingProposal,
    actor,
    section: str,
    decision: str,
) -> OnboardingProposal:
    proposal = _lock_onboarding_proposal(proposal)
    _ensure_proposal_reviewable(proposal)
    _ensure_can_manage_onboarding_proposal(proposal=proposal, actor=actor)

    if section not in PROPOSAL_SECTIONS:
        raise OnboardingProposalValidationError(
            [_proposal_error("unknown_section", section=section)]
        )
    if decision not in PROPOSAL_SECTION_DECISIONS:
        raise OnboardingProposalValidationError(
            [_proposal_error("invalid_payload_type", section=section, field="decision")]
        )
    if section in PROPOSAL_REQUIRED_SECTIONS and decision == PROPOSAL_SECTION_SKIPPED:
        raise OnboardingProposalValidationError(
            [_proposal_error("missing_required_section", section=section)]
        )

    proposal.payload = validate_onboarding_proposal_payload(proposal.payload)
    proposal.validation_errors = []

    if decision == PROPOSAL_SECTION_REJECTED:
        proposal.section_validation[section] = PROPOSAL_SECTION_REJECTED
        proposal.status = OnboardingProposal.Status.REJECTED
        proposal.save(
            update_fields=[
                "payload",
                "section_validation",
                "validation_errors",
                "status",
                "updated_at",
            ]
        )
        return proposal

    section_validation = dict(proposal.section_validation or {})
    section_validation[section] = decision
    section_validation = _normalize_empty_optional_section_decisions(
        payload=proposal.payload,
        section_validation=section_validation,
    )
    proposal.section_validation = section_validation

    if _proposal_sections_are_validated(section_validation):
        proposal.status = OnboardingProposal.Status.VALIDATED
        proposal.validated_by = actor
        proposal.validated_at = timezone.now()
        update_fields = [
            "payload",
            "section_validation",
            "validation_errors",
            "status",
            "validated_by",
            "validated_at",
            "updated_at",
        ]
    else:
        proposal.status = OnboardingProposal.Status.PARTIALLY_VALIDATED
        update_fields = [
            "payload",
            "section_validation",
            "validation_errors",
            "status",
            "updated_at",
        ]

    proposal.save(update_fields=update_fields)
    _set_session_status_after_proposal_validation(proposal.onboarding_session)
    return proposal


@transaction.atomic
def reject_onboarding_proposal(*, proposal: OnboardingProposal, actor) -> OnboardingProposal:
    proposal = _lock_onboarding_proposal(proposal)
    _ensure_proposal_reviewable(proposal)
    _ensure_can_manage_onboarding_proposal(proposal=proposal, actor=actor)

    proposal.status = OnboardingProposal.Status.REJECTED
    proposal.save(update_fields=["status", "updated_at"])
    return proposal


@transaction.atomic
def apply_onboarding_proposal(*, proposal: OnboardingProposal, actor) -> OnboardingProposal:
    proposal = _lock_onboarding_proposal(proposal)
    session = _lock_onboarding_session(proposal.onboarding_session)
    establishment = (
        Establishment.objects.select_for_update()
        .select_related("organization")
        .get(id=proposal.establishment_id)
    )
    _ensure_non_terminal_onboarding_session(session)
    _ensure_can_manage_onboarding_proposal(proposal=proposal, actor=actor)

    if establishment.status != Establishment.Status.DRAFT:
        raise OnboardingProposalStateError("Only draft establishments can apply proposals.")
    if proposal.status != OnboardingProposal.Status.VALIDATED:
        raise OnboardingProposalStateError("Only validated proposals can be applied.")

    payload = validate_onboarding_proposal_payload(proposal.payload)
    source = proposal.source

    module_keys = _apply_keyed_runtime_section(
        model_class=OperationalModule,
        establishment=establishment,
        items=payload["operational_modules"],
        source=source,
        proposal=proposal,
    )
    domain_keys, domains_by_key = _apply_keyed_runtime_section_with_map(
        model_class=OperationalDomain,
        establishment=establishment,
        items=payload["operational_domains"],
        source=source,
        proposal=proposal,
    )
    unit_keys, units_by_key = _apply_keyed_runtime_section_with_map(
        model_class=OperationalUnit,
        establishment=establishment,
        items=payload["operational_units"],
        source=source,
        proposal=proposal,
    )
    _apply_vocabulary_section(
        establishment=establishment,
        items=payload["runtime_vocabulary"],
        domains_by_key=domains_by_key,
        units_by_key=units_by_key,
        source=source,
        proposal=proposal,
    )
    _apply_runtime_tag_section(
        establishment=establishment,
        items=payload["runtime_tags"],
        domains_by_key=domains_by_key,
        source=source,
        proposal=proposal,
    )
    _apply_routing_hint_section(
        establishment=establishment,
        items=payload["routing_hints"],
        domains_by_key=domains_by_key,
        units_by_key=units_by_key,
        source=source,
        proposal=proposal,
    )
    _deactivate_omitted_vocabulary(
        establishment=establishment,
        terms={item["term"] for item in payload["runtime_vocabulary"]},
    )
    _deactivate_omitted_keyed(
        model_class=RuntimeTag,
        establishment=establishment,
        keys={item["key"] for item in payload["runtime_tags"]},
    )
    _deactivate_omitted_routing_hints(
        establishment=establishment,
        patterns={item["pattern"] for item in payload["routing_hints"]},
    )

    proposal.payload = payload
    proposal.status = OnboardingProposal.Status.APPLIED
    proposal.applied_by = actor
    proposal.applied_at = timezone.now()
    proposal.validation_errors = []
    proposal.save(
        update_fields=[
            "payload",
            "status",
            "applied_by",
            "applied_at",
            "validation_errors",
            "updated_at",
        ]
    )

    session.status = OnboardingSession.Status.CONFIGURING_RUNTIME
    session.ready_for_activation_at = None
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    assert module_keys or domain_keys or unit_keys
    return proposal


def _create_onboarding_proposal(
    *,
    session: OnboardingSession,
    actor,
    payload: dict,
    source: str,
) -> OnboardingProposal:
    session = _lock_onboarding_session(session)
    _ensure_non_terminal_onboarding_session(session)

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_configure_runtime:
        raise OnboardingAccessDeniedError

    sanitized_payload = validate_onboarding_proposal_payload(payload)
    proposal = OnboardingProposal(
        onboarding_session=session,
        establishment=session.establishment,
        source=source,
        status=OnboardingProposal.Status.READY,
        payload=sanitized_payload,
        validation_errors=[],
        created_by=actor,
    )
    proposal.full_clean(validate_unique=False, validate_constraints=False)

    try:
        proposal.save()
    except IntegrityError as exc:
        raise ActiveOnboardingProposalExistsError(
            "A non-terminal onboarding proposal already exists for this session."
        ) from exc

    session.status = OnboardingSession.Status.PROPOSAL_READY
    session.ready_for_activation_at = None
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])
    return proposal


def _empty_proposal_payload() -> dict:
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "operational_modules": [],
        "operational_domains": [],
        "operational_units": [],
        "runtime_vocabulary": [],
        "runtime_tags": [],
        "routing_hints": [],
    }


def _active_onboarding_catalog_keys() -> dict[str, set[str]]:
    return {
        "modules": set(
            OnboardingCatalogModule.objects.filter(active=True).values_list(
                "key",
                flat=True,
            )
        ),
        "domains": set(
            OnboardingCatalogDomain.objects.filter(active=True).values_list(
                "key",
                flat=True,
            )
        ),
        "units": set(
            OnboardingCatalogUnit.objects.filter(active=True).values_list(
                "key",
                flat=True,
            )
        ),
    }


def _section_items(payload: dict, section: str, errors: list[dict]) -> list:
    items = payload.get(section, [])
    if not isinstance(items, list):
        errors.append(_proposal_error("section_must_be_array", section=section))
        return []
    if len(items) > PROPOSAL_SECTION_CAPS[section]:
        errors.append(_proposal_error("section_cap_exceeded", section=section))
        return items[: PROPOSAL_SECTION_CAPS[section]]
    return items


def _validate_catalog_keyed_section(
    *,
    section: str,
    items: list,
    allowed_keys: set[str],
    errors: list[dict],
    related_module_keys: set[str] | None = None,
) -> list[dict]:
    sanitized: list[dict] = []
    seen_keys: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section=section))
            continue

        key = _normalized_string(item.get("key"))
        label = _normalized_string(item.get("label"))

        if not key:
            errors.append(_proposal_error("blank_key", section=section, field="key"))
            continue
        if not label:
            errors.append(_proposal_error("blank_label", section=section, key=key, field="label"))
            continue
        if key in seen_keys:
            errors.append(_proposal_error("duplicate_key", section=section, key=key))
            continue
        if key not in allowed_keys:
            errors.append(_proposal_error("unknown_catalog_key", section=section, key=key))
            continue

        related_modules = _normalized_string_list(item.get("related_modules", []))
        if related_module_keys is not None:
            invalid_related_modules = [
                related_key
                for related_key in related_modules
                if related_key not in related_module_keys
            ]
            if invalid_related_modules:
                errors.append(
                    _proposal_error(
                        "invalid_related_module_key",
                        section=section,
                        key=key,
                        field="related_modules",
                    )
                )
                continue

        seen_keys.add(key)
        sanitized_item = {
            "key": key,
            "label": label,
            "reason": _normalized_string(item.get("reason")),
            "confidence_score": item.get("confidence_score"),
        }
        if section in {"operational_domains", "operational_units"}:
            sanitized_item["related_modules"] = related_modules
        sanitized.append(sanitized_item)

    return sanitized


def _validate_vocabulary_section(
    items: list,
    *,
    domain_keys: set[str],
    unit_keys: set[str],
    errors: list[dict],
) -> list[dict]:
    sanitized: list[dict] = []
    seen_terms: set[str] = set()
    section = "runtime_vocabulary"

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section=section))
            continue

        term = _normalized_string(item.get("term"))
        meaning = _normalized_string(item.get("meaning"))
        mapped_domain_key = _nullable_normalized_string(item.get("mapped_domain_key"))
        mapped_unit_key = _nullable_normalized_string(item.get("mapped_unit_key"))

        if not term:
            errors.append(_proposal_error("blank_term", section=section, field="term"))
            continue
        if not meaning:
            errors.append(
                _proposal_error("blank_meaning", section=section, key=term, field="meaning")
            )
            continue
        if term in seen_terms:
            errors.append(_proposal_error("duplicate_term", section=section, key=term))
            continue
        invalid_mapping = False
        if mapped_domain_key is not None and mapped_domain_key not in domain_keys:
            errors.append(
                _proposal_error(
                    "invalid_mapped_domain_key",
                    section=section,
                    key=term,
                    field="mapped_domain_key",
                )
            )
            invalid_mapping = True
        if mapped_unit_key is not None and mapped_unit_key not in unit_keys:
            errors.append(
                _proposal_error(
                    "invalid_mapped_unit_key",
                    section=section,
                    key=term,
                    field="mapped_unit_key",
                )
            )
            invalid_mapping = True
        if invalid_mapping:
            continue

        seen_terms.add(term)
        sanitized.append(
            {
                "term": term,
                "meaning": meaning,
                "mapped_domain_key": mapped_domain_key,
                "mapped_unit_key": mapped_unit_key,
                "reason": _normalized_string(item.get("reason")),
            }
        )

    return sanitized


def _validate_runtime_tag_section(
    items: list,
    *,
    domain_keys: set[str],
    errors: list[dict],
) -> list[dict]:
    sanitized: list[dict] = []
    seen_keys: set[str] = set()
    section = "runtime_tags"

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section=section))
            continue

        key = _normalized_string(item.get("key"))
        label = _normalized_string(item.get("label"))
        related_domain_keys = _normalized_string_list(item.get("related_domain_keys", []))

        if not key:
            errors.append(_proposal_error("blank_key", section=section, field="key"))
            continue
        if not label:
            errors.append(_proposal_error("blank_label", section=section, key=key, field="label"))
            continue
        if key in seen_keys:
            errors.append(_proposal_error("duplicate_key", section=section, key=key))
            continue
        if any(domain_key not in domain_keys for domain_key in related_domain_keys):
            errors.append(
                _proposal_error(
                    "invalid_mapped_domain_key",
                    section=section,
                    key=key,
                    field="related_domain_keys",
                )
            )
            continue

        seen_keys.add(key)
        sanitized.append(
            {
                "key": key,
                "label": label,
                "related_domain_keys": related_domain_keys,
                "reason": _normalized_string(item.get("reason")),
            }
        )

    return sanitized


def _validate_routing_hint_section(
    items: list,
    *,
    domain_keys: set[str],
    unit_keys: set[str],
    errors: list[dict],
) -> list[dict]:
    sanitized: list[dict] = []
    seen_patterns: set[str] = set()
    section = "routing_hints"

    for item in items:
        if not isinstance(item, dict):
            errors.append(_proposal_error("invalid_payload_type", section=section))
            continue

        pattern = _normalized_string(item.get("pattern"))
        suggested_domain_keys = _normalized_string_list(item.get("suggested_domain_keys", []))
        suggested_unit_key = _nullable_normalized_string(item.get("suggested_unit_key"))

        if not pattern:
            errors.append(_proposal_error("blank_pattern", section=section, field="pattern"))
            continue
        if pattern in seen_patterns:
            errors.append(_proposal_error("duplicate_pattern", section=section, key=pattern))
            continue
        if len(suggested_domain_keys) > PROPOSAL_MAX_ROUTING_HINT_DOMAINS:
            errors.append(
                _proposal_error(
                    "too_many_suggested_domains",
                    section=section,
                    key=pattern,
                    field="suggested_domain_keys",
                )
            )
            continue
        invalid_mapping = False
        if any(domain_key not in domain_keys for domain_key in suggested_domain_keys):
            errors.append(
                _proposal_error(
                    "invalid_suggested_domain_key",
                    section=section,
                    key=pattern,
                    field="suggested_domain_keys",
                )
            )
            invalid_mapping = True
        if suggested_unit_key is not None and suggested_unit_key not in unit_keys:
            errors.append(
                _proposal_error(
                    "invalid_suggested_unit_key",
                    section=section,
                    key=pattern,
                    field="suggested_unit_key",
                )
            )
            invalid_mapping = True
        if invalid_mapping:
            continue

        seen_patterns.add(pattern)
        sanitized.append(
            {
                "pattern": pattern,
                "suggested_domain_keys": suggested_domain_keys,
                "suggested_unit_key": suggested_unit_key,
                "reason": _normalized_string(item.get("reason")),
                "confidence_score": item.get("confidence_score"),
            }
        )

    return sanitized


def _proposal_error(
    code: str,
    *,
    section: str | None = None,
    field: str | None = None,
    key: str | None = None,
) -> dict:
    error = {"code": code}
    if section is not None:
        error["section"] = section
    if field is not None:
        error["field"] = field
    if key is not None:
        error["key"] = key
    return error


def _normalized_string(value) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _nullable_normalized_string(value) -> str | None:
    if value is None:
        return None
    normalized = _normalized_string(value)
    return normalized or None


def _normalized_string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        normalized_item = _normalized_string(item)
        if not normalized_item or normalized_item in seen:
            continue
        seen.add(normalized_item)
        normalized.append(normalized_item)
    return normalized


def _ensure_proposal_reviewable(proposal: OnboardingProposal) -> None:
    if proposal.status not in {
        OnboardingProposal.Status.READY,
        OnboardingProposal.Status.PARTIALLY_VALIDATED,
        OnboardingProposal.Status.VALIDATED,
    }:
        raise OnboardingProposalStateError("Proposal cannot be reviewed.")


def _ensure_can_manage_onboarding_proposal(*, proposal: OnboardingProposal, actor) -> None:
    access = get_onboarding_access_context(
        actor=actor,
        session=proposal.onboarding_session,
    )
    if not access.can_manage:
        raise OnboardingAccessDeniedError


def _normalize_empty_optional_section_decisions(
    *,
    payload: dict,
    section_validation: dict,
) -> dict:
    for section in PROPOSAL_OPTIONAL_SECTIONS:
        if section not in section_validation and not payload[section]:
            section_validation[section] = PROPOSAL_SECTION_SKIPPED
    return section_validation


def _proposal_sections_are_validated(section_validation: dict) -> bool:
    return all(
        section_validation.get(section) == PROPOSAL_SECTION_ACCEPTED
        for section in PROPOSAL_REQUIRED_SECTIONS
    ) and all(
        section_validation.get(section) in {PROPOSAL_SECTION_ACCEPTED, PROPOSAL_SECTION_SKIPPED}
        for section in PROPOSAL_OPTIONAL_SECTIONS
    )


def _set_session_status_after_proposal_validation(session: OnboardingSession) -> None:
    session = _lock_onboarding_session(session)
    if session.status != OnboardingSession.Status.VALIDATING_SECTIONS:
        session.status = OnboardingSession.Status.VALIDATING_SECTIONS
        session.ready_for_activation_at = None
        session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])


def _apply_keyed_runtime_section(
    *,
    model_class,
    establishment: Establishment,
    items: list[dict],
    source: str,
    proposal: OnboardingProposal,
) -> set[str]:
    keys, _items_by_key = _apply_keyed_runtime_section_with_map(
        model_class=model_class,
        establishment=establishment,
        items=items,
        source=source,
        proposal=proposal,
    )
    return keys


def _apply_keyed_runtime_section_with_map(
    *,
    model_class,
    establishment: Establishment,
    items: list[dict],
    source: str,
    proposal: OnboardingProposal,
) -> tuple[set[str], dict[str, object]]:
    keys: set[str] = set()
    items_by_key: dict[str, object] = {}

    for item in items:
        runtime_item, _created = model_class.objects.update_or_create(
            establishment=establishment,
            key=item["key"],
            defaults={
                "label": item["label"],
                "source": source,
                "active": True,
                "managed_by_onboarding_proposal": proposal,
            },
        )
        keys.add(item["key"])
        items_by_key[item["key"]] = runtime_item

    _deactivate_omitted_keyed(
        model_class=model_class,
        establishment=establishment,
        keys=keys,
    )
    return keys, items_by_key


def _deactivate_omitted_keyed(*, model_class, establishment: Establishment, keys: set[str]):
    queryset = model_class.objects.filter(
        establishment=establishment,
        active=True,
        managed_by_onboarding_proposal__isnull=False,
    )
    if keys:
        queryset = queryset.exclude(key__in=keys)
    queryset.update(active=False, updated_at=timezone.now())


def _apply_vocabulary_section(
    *,
    establishment: Establishment,
    items: list[dict],
    domains_by_key: dict[str, OperationalDomain],
    units_by_key: dict[str, OperationalUnit],
    source: str,
    proposal: OnboardingProposal,
) -> None:
    for item in items:
        mapped_domain_key = item["mapped_domain_key"]
        mapped_unit_key = item["mapped_unit_key"]
        RuntimeVocabulary.objects.update_or_create(
            establishment=establishment,
            term=item["term"],
            defaults={
                "meaning": item["meaning"],
                "mapped_domain": (
                    None if mapped_domain_key is None else domains_by_key[mapped_domain_key]
                ),
                "mapped_unit": None if mapped_unit_key is None else units_by_key[mapped_unit_key],
                "source": source,
                "active": True,
                "managed_by_onboarding_proposal": proposal,
            },
        )


def _deactivate_omitted_vocabulary(
    *,
    establishment: Establishment,
    terms: set[str],
) -> None:
    queryset = RuntimeVocabulary.objects.filter(
        establishment=establishment,
        active=True,
        managed_by_onboarding_proposal__isnull=False,
    )
    if terms:
        queryset = queryset.exclude(term__in=terms)
    queryset.update(active=False, updated_at=timezone.now())


def _apply_runtime_tag_section(
    *,
    establishment: Establishment,
    items: list[dict],
    domains_by_key: dict[str, OperationalDomain],
    source: str,
    proposal: OnboardingProposal,
) -> None:
    for item in items:
        runtime_tag, _created = RuntimeTag.objects.update_or_create(
            establishment=establishment,
            key=item["key"],
            defaults={
                "label": item["label"],
                "source": source,
                "active": True,
                "managed_by_onboarding_proposal": proposal,
            },
        )
        RuntimeTagDomain.objects.filter(runtime_tag=runtime_tag).delete()
        links = [
            RuntimeTagDomain(
                runtime_tag=runtime_tag,
                operational_domain=domains_by_key[domain_key],
            )
            for domain_key in item["related_domain_keys"]
        ]
        if links:
            RuntimeTagDomain.objects.bulk_create(links)


def _apply_routing_hint_section(
    *,
    establishment: Establishment,
    items: list[dict],
    domains_by_key: dict[str, OperationalDomain],
    units_by_key: dict[str, OperationalUnit],
    source: str,
    proposal: OnboardingProposal,
) -> None:
    for item in items:
        suggested_unit_key = item["suggested_unit_key"]
        routing_hint, _created = RoutingHint.objects.update_or_create(
            establishment=establishment,
            pattern=item["pattern"],
            defaults={
                "suggested_unit": (
                    None if suggested_unit_key is None else units_by_key[suggested_unit_key]
                ),
                "source": source,
                "active": True,
                "managed_by_onboarding_proposal": proposal,
            },
        )
        RoutingHintDomain.objects.filter(routing_hint=routing_hint).delete()
        links = [
            RoutingHintDomain(
                routing_hint=routing_hint,
                operational_domain=domains_by_key[domain_key],
            )
            for domain_key in item["suggested_domain_keys"]
        ]
        if links:
            RoutingHintDomain.objects.bulk_create(links)


def _deactivate_omitted_routing_hints(
    *,
    establishment: Establishment,
    patterns: set[str],
) -> None:
    queryset = RoutingHint.objects.filter(
        establishment=establishment,
        active=True,
        managed_by_onboarding_proposal__isnull=False,
    )
    if patterns:
        queryset = queryset.exclude(pattern__in=patterns)
    queryset.update(active=False, updated_at=timezone.now())


@transaction.atomic
def start_onboarding_session(
    *,
    organization: Organization,
    establishment: Establishment,
    started_by=None,
    source_mode: str = OnboardingSession.SourceMode.MANUAL,
    current_step: str = "",
) -> OnboardingSession:
    if source_mode not in {
        OnboardingSession.SourceMode.MANUAL,
        OnboardingSession.SourceMode.TEMPLATE,
    }:
        raise UnsupportedOnboardingSessionSourceModeError(
            "Only manual and template onboarding sessions are supported."
        )

    if establishment.organization_id != organization.id:
        raise InvalidOnboardingSessionScopeError(
            "Organization must match the establishment organization."
        )

    session = OnboardingSession(
        organization=organization,
        establishment=establishment,
        started_by=started_by,
        source_mode=source_mode,
        current_step=current_step,
    )
    session.full_clean(validate_unique=False, validate_constraints=False)

    try:
        session.save()
    except IntegrityError as exc:
        raise ActiveOnboardingSessionExistsError(
            "A non-terminal onboarding session already exists for this establishment."
        ) from exc

    return session


@transaction.atomic
def submit_activity_description(
    *,
    session: OnboardingSession,
    actor,
    description: str,
) -> EstablishmentActivityDescription:
    session = _lock_onboarding_session(session)
    _ensure_non_terminal_onboarding_session(session)

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_configure_runtime:
        raise OnboardingAccessDeniedError

    normalized_description = _normalize_activity_description(description)
    if len(normalized_description) < ACTIVITY_DESCRIPTION_MIN_LENGTH:
        raise InvalidActivityDescriptionError(
            f"Activity description must be at least {ACTIVITY_DESCRIPTION_MIN_LENGTH} characters."
        )

    activity_description, _created = EstablishmentActivityDescription.objects.update_or_create(
        establishment=session.establishment,
        defaults={
            "description": normalized_description,
            "source": EstablishmentActivityDescription.Source.MANUAL,
            "submitted_by": actor,
            "validated_at": timezone.now(),
        },
    )
    try:
        activity_description.full_clean()
    except ValidationError as exc:
        raise InvalidActivityDescriptionError(str(exc)) from exc

    activity_description.save(
        update_fields=[
            "description",
            "source",
            "submitted_by",
            "validated_at",
            "updated_at",
        ],
    )

    _set_status_after_description_submit(session)
    return activity_description


def compute_activation_readiness(*, session: OnboardingSession) -> dict:
    session = _reload_onboarding_session(session)
    config = get_runtime_config_for_session(session=session)
    description = config["activity_description"]

    counts = _activation_counts(session)
    sections = {
        "description": {
            "is_ready": _is_valid_activity_description(description),
            "required": True,
            "is_skippable": False,
        },
        "modules": {
            "is_ready": counts["active_modules_count"] >= 1,
            "required": True,
            "is_skippable": False,
        },
        "domains": {
            "is_ready": counts["active_domains_count"] >= 3,
            "required": True,
            "is_skippable": False,
        },
        "units": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "vocabulary": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "runtime_tags": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "routing_hints": {
            "is_ready": True,
            "required": False,
            "is_skippable": True,
        },
        "managers": {
            "is_ready": (
                counts["active_or_invited_manager_count"] >= 1
                and counts["managers_with_domains_count"]
                == counts["active_or_invited_manager_count"]
            ),
            "required": True,
            "is_skippable": False,
        },
    }
    blockers = _activation_blockers(
        session=session,
        description=description,
        counts=counts,
    )

    return {
        "is_ready": not blockers,
        "blockers": blockers,
        "counts": counts,
        "sections": sections,
        "establishment_status": session.establishment.status,
        "session_status": session.status,
    }


def build_activation_summary(*, session: OnboardingSession) -> dict:
    session = _reload_onboarding_session(session)
    config = get_runtime_config_for_session(session=session)
    readiness = compute_activation_readiness(session=session)
    counts = readiness["counts"]

    return {
        "organization": _serialize_organization(session.organization),
        "establishment": _serialize_establishment(session.establishment),
        "activity_description": _serialize_activity_description(
            config["activity_description"],
        ),
        "active_modules": [
            _serialize_keyed_runtime_item(item) for item in config["active_modules"]
        ],
        "active_domains": [
            _serialize_keyed_runtime_item(item) for item in config["active_domains"]
        ],
        "optional_units": [
            _serialize_keyed_runtime_item(item) for item in config["optional_units"]
        ],
        "optional_vocabulary": [
            _serialize_vocabulary_item(item) for item in config["optional_vocabulary"]
        ],
        "optional_runtime_tags": [
            _serialize_runtime_tag(item) for item in config["optional_runtime_tags"]
        ],
        "optional_routing_hints": [
            _serialize_routing_hint(item) for item in config["optional_routing_hints"]
        ],
        "initial_owner_director_count": counts["active_owner_or_director_count"],
        "initial_manager_count": counts["active_or_invited_manager_count"],
        "managers_with_domains_count": counts["managers_with_domains_count"],
        "readiness": readiness,
        "blockers": readiness["blockers"],
    }


@transaction.atomic
def mark_onboarding_ready_for_activation(
    *,
    session: OnboardingSession,
    actor,
) -> dict:
    session = _lock_onboarding_session(session)
    _ensure_non_terminal_onboarding_session(session)

    access = get_onboarding_access_context(actor=actor, session=session)
    if not access.can_activate:
        raise OnboardingAccessDeniedError

    readiness = compute_activation_readiness(session=session)
    effective_can_activate = readiness["is_ready"] and access.can_activate
    if not effective_can_activate:
        raise OnboardingReadinessError(readiness)

    if session.status != OnboardingSession.Status.READY_FOR_ACTIVATION:
        session.status = OnboardingSession.Status.READY_FOR_ACTIVATION
    session.ready_for_activation_at = timezone.now()
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])

    return {
        "session": session,
        "readiness": readiness,
        "access": access,
        "effective_can_activate": effective_can_activate,
    }


@transaction.atomic
def update_membership_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
    update_input: MembershipUpdateInput,
) -> EstablishmentMembership:
    membership = get_membership_for_management(
        current_membership=current_membership,
        establishment_id=establishment_id,
        membership_id=membership_id,
    )
    if membership is None:
        raise MembershipManagementNotFoundError

    update_fields: list[str] = []

    if update_input.role is not None and membership.role != update_input.role:
        if _would_demote_last_active_owner(
            membership=membership,
            next_role=update_input.role,
        ):
            raise CannotDemoteLastActiveOwnerError

        membership.role = update_input.role
        update_fields.append("role")

    if update_fields:
        membership.save(update_fields=[*update_fields, "updated_at"])

    if update_input.operational_domains is not None:
        _replace_membership_domains(
            membership=membership,
            operational_domain_keys=update_input.operational_domains,
        )

    membership.refresh_from_db()
    return _reload_membership_for_response(membership.id)


@transaction.atomic
def deactivate_membership_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
) -> EstablishmentMembership:
    membership = get_membership_for_management(
        current_membership=current_membership,
        establishment_id=establishment_id,
        membership_id=membership_id,
    )
    if membership is None:
        raise MembershipManagementNotFoundError

    if (
        membership.status == EstablishmentMembership.Status.ACTIVE
        and membership.role == EstablishmentMembership.Role.OWNER
        and _is_last_active_owner(membership)
    ):
        raise CannotDeactivateLastActiveOwnerError

    if membership.status != EstablishmentMembership.Status.DEACTIVATED:
        membership.status = EstablishmentMembership.Status.DEACTIVATED
        membership.save(update_fields=["status", "updated_at"])

    _clear_selected_establishment_for_membership(membership)

    membership.refresh_from_db()
    return _reload_membership_for_response(membership.id)


def _lock_onboarding_session(session: OnboardingSession) -> OnboardingSession:
    return (
        OnboardingSession.objects.select_for_update()
        .select_related("organization", "establishment", "establishment__organization")
        .get(id=session.id)
    )


def _lock_onboarding_proposal(proposal: OnboardingProposal) -> OnboardingProposal:
    return (
        OnboardingProposal.objects.select_for_update()
        .select_related(
            "establishment",
            "establishment__organization",
            "onboarding_session",
            "onboarding_session__organization",
            "onboarding_session__establishment",
            "onboarding_session__establishment__organization",
        )
        .get(id=proposal.id)
    )


def _reload_onboarding_session(session: OnboardingSession) -> OnboardingSession:
    return OnboardingSession.objects.select_related(
        "organization",
        "establishment",
        "establishment__organization",
    ).get(id=session.id)


def _ensure_non_terminal_onboarding_session(session: OnboardingSession) -> None:
    if OnboardingSession.is_terminal_status(session.status):
        raise OnboardingSessionTerminalError


def _normalize_activity_description(description: str) -> str:
    if not isinstance(description, str):
        raise InvalidActivityDescriptionError("Activity description must be a string.")

    return description.strip()


def _set_status_after_description_submit(session: OnboardingSession) -> None:
    if session.status in {
        OnboardingSession.Status.STARTED,
        OnboardingSession.Status.DESCRIPTION_SUBMITTED,
    }:
        next_status = OnboardingSession.Status.DESCRIPTION_SUBMITTED
    elif session.status == OnboardingSession.Status.READY_FOR_ACTIVATION:
        next_status = OnboardingSession.Status.VALIDATING_SECTIONS
    else:
        next_status = OnboardingSession.Status.CONFIGURING_RUNTIME

    session.status = next_status
    if next_status != OnboardingSession.Status.READY_FOR_ACTIVATION:
        session.ready_for_activation_at = None
    session.save(update_fields=["status", "ready_for_activation_at", "updated_at"])


def _activation_counts(session: OnboardingSession) -> dict:
    establishment_id = session.establishment_id
    managers = EstablishmentMembership.objects.filter(
        establishment_id=establishment_id,
        role=EstablishmentMembership.Role.MANAGER,
        status__in=[
            EstablishmentMembership.Status.ACTIVE,
            EstablishmentMembership.Status.INVITED,
        ],
    )
    managers_with_domains_count = (
        managers.annotate(
            active_domains_count=Count(
                "domain_links",
                filter=Q(
                    domain_links__operational_domain__active=True,
                    domain_links__operational_domain__establishment_id=establishment_id,
                ),
                distinct=True,
            )
        )
        .filter(active_domains_count__gte=1)
        .count()
    )

    return {
        "active_modules_count": session.establishment.operational_modules.filter(
            active=True,
        ).count(),
        "active_domains_count": session.establishment.operational_domains.filter(
            active=True,
        ).count(),
        "active_owner_or_director_count": EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            role__in=[
                EstablishmentMembership.Role.OWNER,
                EstablishmentMembership.Role.DIRECTOR,
            ],
        ).count(),
        "active_or_invited_manager_count": managers.count(),
        "managers_with_domains_count": managers_with_domains_count,
    }


def _activation_blockers(
    *,
    session: OnboardingSession,
    description: EstablishmentActivityDescription | None,
    counts: dict,
) -> list[dict]:
    blockers: list[dict] = []

    if OnboardingSession.is_terminal_status(session.status):
        blockers.append(_blocker("session_terminal"))

    if session.organization.status != Organization.Status.ACTIVE:
        blockers.append(_blocker("organization_not_active"))

    if session.establishment.status != Establishment.Status.DRAFT:
        blockers.append(_blocker("establishment_not_draft"))

    if description is None or description.validated_at is None:
        blockers.append(_blocker("missing_validated_description"))
    elif len((description.description or "").strip()) < ACTIVITY_DESCRIPTION_MIN_LENGTH:
        blockers.append(_blocker("description_too_short"))

    if counts["active_modules_count"] < 1:
        blockers.append(_blocker("missing_active_module"))

    if counts["active_domains_count"] < 3:
        blockers.append(_blocker("insufficient_active_domains"))

    if counts["active_owner_or_director_count"] < 1:
        blockers.append(_blocker("missing_active_owner_or_director"))

    if counts["active_or_invited_manager_count"] < 1:
        blockers.append(_blocker("missing_active_or_invited_manager"))
    elif counts["managers_with_domains_count"] != counts["active_or_invited_manager_count"]:
        blockers.append(_blocker("manager_domains_missing"))

    return blockers


def _blocker(code: str) -> dict:
    return {"code": code, "message": code.replace("_", " ")}


def _is_valid_activity_description(
    description: EstablishmentActivityDescription | None,
) -> bool:
    return (
        description is not None
        and description.validated_at is not None
        and len((description.description or "").strip()) >= ACTIVITY_DESCRIPTION_MIN_LENGTH
    )


def _serialize_organization(organization: Organization) -> dict:
    return {
        "id": str(organization.id),
        "name": organization.name,
        "status": organization.status,
    }


def _serialize_establishment(establishment: Establishment) -> dict:
    return {
        "id": str(establishment.id),
        "name": establishment.name,
        "status": establishment.status,
    }


def _serialize_activity_description(
    description: EstablishmentActivityDescription | None,
) -> dict | None:
    if description is None:
        return None

    return {
        "id": str(description.id),
        "description": description.description,
        "source": description.source,
        "submitted_by_id": (
            None if description.submitted_by_id is None else str(description.submitted_by_id)
        ),
        "validated_at": description.validated_at,
    }


def _serialize_keyed_runtime_item(item) -> dict:
    return {
        "id": str(item.id),
        "key": item.key,
        "label": item.label,
        "source": item.source,
        "active": item.active,
    }


def _serialize_vocabulary_item(item) -> dict:
    return {
        "id": str(item.id),
        "term": item.term,
        "meaning": item.meaning,
        "mapped_domain_key": (None if item.mapped_domain_id is None else item.mapped_domain.key),
        "mapped_unit_key": None if item.mapped_unit_id is None else item.mapped_unit.key,
        "source": item.source,
        "active": item.active,
    }


def _serialize_runtime_tag(runtime_tag) -> dict:
    return {
        "id": str(runtime_tag.id),
        "key": runtime_tag.key,
        "label": runtime_tag.label,
        "source": runtime_tag.source,
        "active": runtime_tag.active,
        "domain_keys": [link.operational_domain.key for link in runtime_tag.domain_links.all()],
    }


def _serialize_routing_hint(routing_hint) -> dict:
    return {
        "id": str(routing_hint.id),
        "pattern": routing_hint.pattern,
        "suggested_unit_key": (
            None if routing_hint.suggested_unit_id is None else routing_hint.suggested_unit.key
        ),
        "source": routing_hint.source,
        "active": routing_hint.active,
        "domain_keys": [link.operational_domain.key for link in routing_hint.domain_links.all()],
    }


def _replace_membership_domains(
    *,
    membership: EstablishmentMembership,
    operational_domain_keys: list[str],
) -> None:
    normalized_keys = _normalize_domain_keys(operational_domain_keys)
    domains_by_key = {
        domain.key: domain
        for domain in OperationalDomain.objects.filter(
            establishment=membership.establishment,
            active=True,
            key__in=normalized_keys,
        ).only("id", "key")
    }

    if len(domains_by_key) != len(normalized_keys):
        raise InvalidMembershipDomainAssignmentError(
            "Operational domains must be active and belong to the same establishment."
        )

    requested_domain_ids = {domains_by_key[key].id for key in normalized_keys}

    MembershipDomain.objects.filter(membership=membership).exclude(
        operational_domain_id__in=requested_domain_ids
    ).delete()

    existing_domain_ids = set(
        MembershipDomain.objects.filter(membership=membership).values_list(
            "operational_domain_id",
            flat=True,
        )
    )
    missing_links = [
        MembershipDomain(
            membership=membership,
            operational_domain=domains_by_key[key],
        )
        for key in normalized_keys
        if domains_by_key[key].id not in existing_domain_ids
    ]
    if missing_links:
        MembershipDomain.objects.bulk_create(missing_links)


def _normalize_domain_keys(domain_keys: list[str]) -> list[str]:
    normalized_keys: list[str] = []
    seen_keys: set[str] = set()

    for domain_key in domain_keys:
        if not isinstance(domain_key, str):
            raise InvalidMembershipDomainAssignmentError(
                "Operational domain keys must be non-empty strings."
            )

        normalized_key = domain_key.strip()
        if not normalized_key:
            raise InvalidMembershipDomainAssignmentError(
                "Operational domain keys must be non-empty strings."
            )

        if normalized_key in seen_keys:
            continue

        seen_keys.add(normalized_key)
        normalized_keys.append(normalized_key)

    return normalized_keys


def _is_last_active_owner(membership: EstablishmentMembership) -> bool:
    return (
        EstablishmentMembership.objects.filter(
            establishment=membership.establishment,
            status=EstablishmentMembership.Status.ACTIVE,
            role=EstablishmentMembership.Role.OWNER,
        )
        .exclude(id=membership.id)
        .count()
        == 0
    )


def _would_demote_last_active_owner(
    *,
    membership: EstablishmentMembership,
    next_role: str,
) -> bool:
    return (
        membership.status == EstablishmentMembership.Status.ACTIVE
        and membership.role == EstablishmentMembership.Role.OWNER
        and next_role != EstablishmentMembership.Role.OWNER
        and _is_last_active_owner(membership)
    )


def _clear_selected_establishment_for_membership(
    membership: EstablishmentMembership,
) -> None:
    UserSession.objects.filter(
        user=membership.user,
        selected_establishment=membership.establishment,
    ).update(
        selected_establishment=None,
        updated_at=timezone.now(),
    )


def _reload_membership_for_response(membership_id) -> EstablishmentMembership:
    return (
        EstablishmentMembership.objects.select_related(
            "user",
            "establishment",
            "establishment__organization",
        )
        .prefetch_related("domain_links__operational_domain")
        .get(id=membership_id)
    )
