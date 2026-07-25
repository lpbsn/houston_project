from __future__ import annotations

import uuid
from dataclasses import dataclass

from houston.establishments.business_unit_identity import (
    build_business_unit_routing_key,
    build_free_activity_subject_routing_key,
    normalize_business_unit_specific_name,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name
from houston.signals.models import Signal

RESTAURANT_MODULE_KEY = "restaurant"


@dataclass(frozen=True)
class RestaurantBusinessUnits:
    restaurant: BusinessUnit
    maintenance: BusinessUnit
    bar: BusinessUnit


@dataclass(frozen=True)
class RestaurantV3Taxonomy:
    restaurant: BusinessUnit
    maintenance: BusinessUnit | None
    bar: BusinessUnit
    lighting_subject: ActivitySubject | None
    stock_subject: ActivitySubject | None


def create_business_unit(
    *,
    establishment: Establishment,
    key: str,
    label: str | None = None,
    description: str = "",
    unit_type: str = BusinessUnit.UnitType.DEDICATED,
) -> BusinessUnit:
    label_value = label or key.replace("_", " ").title()
    catalog, _ = CatalogBusinessUnit.objects.get_or_create(
        key=key,
        defaults={
            "label": label_value,
            "description": "",
            "unit_type": unit_type,
            "active": True,
            "sort_order": 0,
        },
    )
    normalized = normalize_business_unit_specific_name(label_value)
    existing = BusinessUnit.objects.filter(
        establishment=establishment,
        normalized_specific_name=normalized,
    ).first()
    if existing is not None:
        return existing
    business_unit_id = uuid.uuid4()
    return BusinessUnit.objects.create(
        id=business_unit_id,
        establishment=establishment,
        catalog_business_unit=catalog,
        specific_name=label_value,
        normalized_specific_name=normalized,
        routing_key=build_business_unit_routing_key(
            business_unit_id=business_unit_id,
            catalog_key=catalog.key,
            specific_name=label_value,
        ),
        instance_description=description,
        source=BusinessUnit.Source.MANUAL,
        active=True,
    )


def create_activity_subject(
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
    label: str,
    description: str = "",
) -> ActivitySubject:
    activity_subject_id = uuid.uuid4()
    return ActivitySubject.objects.create(
        id=activity_subject_id,
        establishment=establishment,
        business_unit=business_unit,
        normalized_name=normalize_activity_subject_name(label),
        label=label,
        description=description,
        routing_key=build_free_activity_subject_routing_key(
            activity_subject_id=activity_subject_id,
            label=label,
        ),
        source=ActivitySubject.Source.MANUAL,
        active=True,
    )


def create_membership_with_business_unit_scope(
    *,
    membership: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> MembershipScope:
    return MembershipScope.objects.create(
        membership=membership,
        business_unit=business_unit,
    )


def business_unit_scope_payload(business_unit: BusinessUnit) -> dict[str, str]:
    return {
        "scope_type": "business_unit",
        "scope_id": str(business_unit.id),
        "scope_label": business_unit.specific_name or str(business_unit.id),
    }


def assert_business_unit_scope_response(body: dict, *, business_unit: BusinessUnit) -> None:
    assert body["scopes"] == [business_unit_scope_payload(business_unit)]
    assert body["scope_summary"] == {"business_unit_count": 1}


def hotel_maintenance_setup(establishment: Establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
    )
    maintenance = create_business_unit(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        unit_type=BusinessUnit.UnitType.TRANSVERSAL,
    )
    electricite = create_activity_subject(
        establishment=establishment,
        business_unit=maintenance,
        label="Électricité",
    )
    return hotel, maintenance, electricite


def _get_or_create_business_unit(
    *,
    establishment: Establishment,
    key: str,
    label: str,
    unit_type: str = BusinessUnit.UnitType.DEDICATED,
) -> BusinessUnit:
    return create_business_unit(
        establishment=establishment,
        key=key,
        label=label,
        unit_type=unit_type,
    )


def _get_or_create_activity_subject(
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
    label: str,
) -> ActivitySubject:
    normalized_name = normalize_activity_subject_name(label)
    existing = ActivitySubject.objects.filter(
        business_unit=business_unit,
        normalized_name=normalized_name,
    ).first()
    if existing is not None:
        if not existing.routing_key:
            existing.routing_key = build_free_activity_subject_routing_key(
                activity_subject_id=existing.id,
                label=existing.label or label,
            )
            existing.save(update_fields=["routing_key", "updated_at"])
        return existing
    return create_activity_subject(
        establishment=establishment,
        business_unit=business_unit,
        label=label,
    )


def create_restaurant_business_units(establishment: Establishment) -> RestaurantBusinessUnits:
    return RestaurantBusinessUnits(
        restaurant=_get_or_create_business_unit(
            establishment=establishment,
            key=RESTAURANT_MODULE_KEY,
            label="Restaurant",
        ),
        maintenance=_get_or_create_business_unit(
            establishment=establishment,
            key="maintenance",
            label="Maintenance",
            unit_type=BusinessUnit.UnitType.TRANSVERSAL,
        ),
        bar=_get_or_create_business_unit(
            establishment=establishment,
            key="bar",
            label="Bar",
        ),
    )


def create_restaurant_v3_taxonomy(
    establishment: Establishment,
    *,
    include_maintenance_transversal: bool = True,
    include_lighting_subject: bool = True,
    include_bar_stock: bool = True,
) -> RestaurantV3Taxonomy:
    restaurant = _get_or_create_business_unit(
        establishment=establishment,
        key=RESTAURANT_MODULE_KEY,
        label="Restaurant",
    )
    maintenance = None
    lighting_subject = None
    if include_maintenance_transversal:
        maintenance = _get_or_create_business_unit(
            establishment=establishment,
            key="maintenance",
            label="Maintenance",
            unit_type=BusinessUnit.UnitType.TRANSVERSAL,
        )
        if include_lighting_subject:
            lighting_subject = _get_or_create_activity_subject(
                establishment=establishment,
                business_unit=maintenance,
                label="Électricité",
            )
    bar = _get_or_create_business_unit(
        establishment=establishment,
        key="bar",
        label="Bar",
    )
    stock_subject = None
    if include_bar_stock:
        stock_subject = _get_or_create_activity_subject(
            establishment=establishment,
            business_unit=bar,
            label="Stock",
        )
    return RestaurantV3Taxonomy(
        restaurant=restaurant,
        maintenance=maintenance,
        bar=bar,
        lighting_subject=lighting_subject,
        stock_subject=stock_subject,
    )


def create_v3_signal(
    establishment: Establishment,
    *,
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject: ActivitySubject,
    routing_status: str,
    title: str = "Signal title",
    structured_summary: str = "Structured summary safe.",
    status: str = Signal.Status.OPEN,
    location_text: str = "",
    issue_focus: str | None = None,
) -> Signal:
    from django.utils import timezone

    from houston.signals.services import normalize_issue_focus

    now = timezone.now()
    stored_issue_focus = normalize_issue_focus(title) if issue_focus is None else issue_focus
    return Signal.objects.create(
        establishment=establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        title=title,
        structured_summary=structured_summary,
        location_text=location_text,
        issue_focus=stored_issue_focus,
        status=status,
        routing_status=routing_status,
        last_activity_at=now,
    )


def create_minimal_v3_signal(
    membership: EstablishmentMembership,
    *,
    title: str = "Signal title",
    status: str = Signal.Status.OPEN,
    routing_status: str = Signal.RoutingStatus.RESOLVED,
) -> Signal:
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    return create_v3_signal(
        membership.establishment,
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
        title=title,
        status=status,
        routing_status=routing_status,
    )


def create_signal_v3_for_membership(
    membership: EstablishmentMembership,
    *,
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject: ActivitySubject,
    status: str = Signal.Status.OPEN,
    title: str = "Signal title",
    location_text: str = "chambre 102",
    issue_focus: str | None = None,
    routing_status: str = Signal.RoutingStatus.RESOLVED,
) -> Signal:
    return create_v3_signal(
        membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        title=title,
        location_text=location_text,
        issue_focus=issue_focus,
        status=status,
        routing_status=routing_status,
    )
