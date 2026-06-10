from __future__ import annotations

import pytest

from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.pipeline import (  # noqa: F401
    GOLDEN_OBSERVATION_TEXT,
    classify_golden_restaurant_signals,
    create_observation,
    golden_two_candidate_pipeline_output,
    signal_detail_url,
    signal_feed_url,
)
from houston.testing.taxonomy import (
    RESTAURANT_MODULE_KEY,
    RestaurantBusinessUnits,
    RestaurantV3Taxonomy,
    create_minimal_v3_signal,
    create_restaurant_business_units,
    create_restaurant_v3_taxonomy,
    create_v3_signal,
)

__all__ = [
    "GOLDEN_OBSERVATION_TEXT",
    "RESTAURANT_MODULE_KEY",
    "RestaurantBusinessUnits",
    "RestaurantV3Taxonomy",
    "api_client",
    "auth_headers",
    "build_api_membership",
    "classify_golden_restaurant_signals",
    "create_minimal_v3_signal",
    "create_observation",
    "create_restaurant_business_units",
    "create_restaurant_v3_taxonomy",
    "create_v3_signal",
    "golden_two_candidate_pipeline_output",
    "login",
    "signal_detail_url",
    "signal_feed_url",
]


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient(enforce_csrf_checks=True)
