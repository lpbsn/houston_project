from __future__ import annotations

import pytest

from houston.ai.observation_pipeline import build_pipeline_input
from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.signals.tests.conftest import create_observation
from houston.testing.factories import build_membership
from houston.testing.query_baseline import (
    OBSERVATION_PIPELINE_INPUT_BUILD_MAX_QUERIES,
    assert_query_count_at_most,
    capture_queries,
)

pytestmark = pytest.mark.django_db


def _setup_taxonomy(establishment):
    hotel = create_business_unit(
        establishment=establishment,
        key="hotel",
        label="Hotel",
    )
    create_activity_subject(
        establishment=establishment,
        business_unit=hotel,
        label="Maintenance",
    )


def test_build_pipeline_input_query_count_baseline():
    membership = build_membership()
    _setup_taxonomy(membership.establishment)
    observation = create_observation(membership=membership, text="Chambre 104 clim HS")

    with capture_queries() as context:
        payload = build_pipeline_input(observation=observation)

    assert payload["observation_id"] == str(observation.id)
    assert_query_count_at_most(
        context,
        max_queries=OBSERVATION_PIPELINE_INPUT_BUILD_MAX_QUERIES,
        label="build_pipeline_input",
    )
