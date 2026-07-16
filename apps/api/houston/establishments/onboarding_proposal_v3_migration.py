"""Convert or reject persisted onboarding_proposal_v3 non-terminal rows."""

from __future__ import annotations

from typing import Any

from houston.establishments.models import OnboardingProposal

PROPOSAL_SCHEMA_VERSION_V3 = "onboarding_proposal_v3"
PROPOSAL_SCHEMA_VERSION_V4 = "onboarding_proposal_v4"
UNSUPPORTED_SCHEMA_VERSION_V3 = "unsupported_schema_version_v3"


def try_convert_v3_payload_to_v4(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort v3 → v4 conversion. Returns None when conversion is unsafe."""
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V3:
        return None

    raw_business_units = payload.get("business_units")
    raw_activity_subjects = payload.get("activity_subjects")
    if not isinstance(raw_business_units, list) or not isinstance(raw_activity_subjects, list):
        return None

    business_units: list[dict[str, Any]] = []
    for item in raw_business_units:
        if not isinstance(item, dict):
            return None
        client_key = item.get("client_key")
        catalog_key = item.get("catalog_key")
        label = item.get("label")
        if not isinstance(client_key, str) or not client_key.strip():
            return None
        if not isinstance(catalog_key, str) or not catalog_key.strip():
            return None
        if not isinstance(label, str) or not label.strip():
            return None
        description = item.get("description", "")
        if description is None:
            description = ""
        if not isinstance(description, str):
            return None
        business_units.append(
            {
                "client_key": client_key,
                "catalog_key": catalog_key.strip(),
                "specific_name": label.strip(),
                "instance_description": description,
            }
        )

    activity_subjects: list[dict[str, Any]] = []
    for item in raw_activity_subjects:
        if not isinstance(item, dict):
            return None
        client_key = item.get("client_key")
        business_unit_client_key = item.get("business_unit_client_key")
        if not isinstance(client_key, str) or not client_key.strip():
            return None
        if not isinstance(business_unit_client_key, str) or not business_unit_client_key.strip():
            return None
        catalog_key = item.get("catalog_key")
        if catalog_key is not None and not isinstance(catalog_key, str):
            return None
        label = item.get("label")
        if label is not None and not isinstance(label, str):
            return None
        description = item.get("description", "")
        if description is None:
            description = ""
        if not isinstance(description, str):
            return None
        subject: dict[str, Any] = {
            "client_key": client_key,
            "business_unit_client_key": business_unit_client_key,
        }
        if isinstance(catalog_key, str) and catalog_key.strip():
            # Catalog identity wins; omit label/description for v4 XOR.
            subject["catalog_key"] = catalog_key.strip()
        elif isinstance(label, str) and label.strip():
            subject["catalog_key"] = None
            subject["label"] = label
            subject["description"] = description
        else:
            return None
        activity_subjects.append(subject)

    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION_V4,
        "business_units": business_units,
        "activity_subjects": activity_subjects,
    }


def process_non_terminal_v3_proposals(*, dry_run: bool = False) -> dict[str, int]:
    """Convert convertible non-terminal v3 proposals; otherwise REJECTED + last_error_code."""
    counts = {
        "scanned": 0,
        "converted": 0,
        "rejected": 0,
        "terminal_left": 0,
        "non_v3": 0,
    }
    proposals = OnboardingProposal.objects.all().iterator()
    for proposal in proposals:
        payload = proposal.payload if isinstance(proposal.payload, dict) else {}
        schema_version = payload.get("schema_version")
        if schema_version != PROPOSAL_SCHEMA_VERSION_V3:
            counts["non_v3"] += 1
            continue
        counts["scanned"] += 1
        if not OnboardingProposal.is_non_terminal_status(proposal.status):
            counts["terminal_left"] += 1
            continue

        converted = try_convert_v3_payload_to_v4(payload)
        if converted is not None:
            counts["converted"] += 1
            if not dry_run:
                proposal.payload = converted
                proposal.section_validation = {}
                proposal.validation_errors = []
                proposal.last_error_code = ""
                proposal.save(
                    update_fields=[
                        "payload",
                        "section_validation",
                        "validation_errors",
                        "last_error_code",
                        "updated_at",
                    ]
                )
            continue

        counts["rejected"] += 1
        if not dry_run:
            proposal.status = OnboardingProposal.Status.REJECTED
            proposal.last_error_code = UNSUPPORTED_SCHEMA_VERSION_V3
            proposal.save(update_fields=["status", "last_error_code", "updated_at"])
    return counts


def assert_no_non_terminal_v3_proposals() -> None:
    remaining = []
    for proposal in OnboardingProposal.objects.filter(
        status__in=OnboardingProposal.NON_TERMINAL_STATUSES
    ).iterator():
        payload = proposal.payload if isinstance(proposal.payload, dict) else {}
        if payload.get("schema_version") == PROPOSAL_SCHEMA_VERSION_V3:
            remaining.append(str(proposal.id))
    if remaining:
        preview = ", ".join(remaining[:20])
        raise RuntimeError(
            "Non-terminal onboarding_proposal_v3 rows remain after processing: "
            f"{preview}"
            + ("…" if len(remaining) > 20 else "")
        )


def inventory_onboarding_v3_proposals() -> dict[str, int]:
    counts = {
        "v3_non_terminal": 0,
        "v3_terminal": 0,
        "other": 0,
    }
    for proposal in OnboardingProposal.objects.all().iterator():
        payload = proposal.payload if isinstance(proposal.payload, dict) else {}
        if payload.get("schema_version") != PROPOSAL_SCHEMA_VERSION_V3:
            counts["other"] += 1
            continue
        if OnboardingProposal.is_non_terminal_status(proposal.status):
            counts["v3_non_terminal"] += 1
        else:
            counts["v3_terminal"] += 1
    return counts
