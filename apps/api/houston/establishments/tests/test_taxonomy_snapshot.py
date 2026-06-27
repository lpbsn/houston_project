from __future__ import annotations

import pytest

from houston.establishments.taxonomy_snapshot import build_establishment_taxonomy_snapshot
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_establishment,
)
from houston.testing.query_baseline import capture_queries

pytestmark = pytest.mark.django_db


@pytest.mark.django_db
def test_snapshot_includes_business_unit_descriptions_and_subjects():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hôtel",
        description="Chambres et couloirs.",
        unit_type="dedicated",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Propreté chambre",
        description="Nettoyage des chambres.",
    )

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)

    assert len(snapshot["business_units"]) == 1
    unit = snapshot["business_units"][0]
    assert unit["key"] == "hotel"
    assert unit["description"] == "Chambres et couloirs."
    assert unit["unit_type"] == "dedicated"
    assert unit["activity_subjects"][0]["key"] == "proprete_chambre"
    assert unit["activity_subjects"][0]["description"] == "Nettoyage des chambres."


@pytest.mark.django_db
def test_snapshot_empty_when_no_active_business_units():
    establishment = create_establishment()

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)

    assert snapshot["business_units"] == []


def test_snapshot_excludes_inactive_activity_subjects():
    establishment = create_establishment()
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Active subject",
    )
    inactive = create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Inactive subject",
    )
    inactive.active = False
    inactive.save(update_fields=["active", "updated_at"])

    snapshot = build_establishment_taxonomy_snapshot(establishment_id=establishment.id)

    assert len(snapshot["business_units"]) == 1
    assert len(snapshot["business_units"][0]["activity_subjects"]) == 1
    assert snapshot["business_units"][0]["activity_subjects"][0]["label"] == "Active subject"


def test_snapshot_query_count_flat_across_business_units():
    one_bu_establishment = create_establishment(name="One BU")
    single_unit = create_business_unit(
        establishment=one_bu_establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=one_bu_establishment,
        business_unit=single_unit,
        label="Maintenance",
    )

    three_bu_establishment = create_establishment(name="Three BU")
    for key, label in (("hotel", "Hotel"), ("bar", "Bar"), ("kitchen", "Kitchen")):
        unit = create_business_unit(
            establishment=three_bu_establishment,
            key=key,
            label=label,
        )
        create_activity_subject(
            establishment=three_bu_establishment,
            business_unit=unit,
            label=f"{label} subject",
        )

    with capture_queries() as one_bu_context:
        build_establishment_taxonomy_snapshot(establishment_id=one_bu_establishment.id)
    with capture_queries() as three_bu_context:
        build_establishment_taxonomy_snapshot(establishment_id=three_bu_establishment.id)

    assert len(one_bu_context.captured_queries) == len(three_bu_context.captured_queries)
