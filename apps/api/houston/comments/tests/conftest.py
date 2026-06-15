from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.testing.auth import auth_headers, build_api_membership, login

__all__ = ["api_client", "auth_headers", "build_api_membership", "login"]


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def signal_comments_url(establishment_id, signal_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/signals/{signal_id}/comments/"


def action_comments_url(establishment_id, action_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/actions/{action_id}/comments/"
