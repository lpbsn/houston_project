from __future__ import annotations

import pytest

from houston.establishments.taxonomy_snapshot import build_establishment_taxonomy_snapshot
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
    create_establishment,
)


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
