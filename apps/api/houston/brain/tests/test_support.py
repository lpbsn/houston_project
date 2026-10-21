"""Shared admission fixture for lifecycle tests. The broker publish is local."""

from __future__ import annotations

import uuid

from houston.brain.tests.test_admission import _admit, _reporting
from houston.establishments.models import EstablishmentMembership
from houston.testing.factories import create_establishment, create_membership

_PUBLISH = "houston.brain.runtime.publish_brain_analysis"


def allow_publish(monkeypatch):
    monkeypatch.setattr(_PUBLISH, lambda *args, **kwargs: True)


def prepare(settings, texts: list[str], *, per_call: int | None = None, total: int | None = None):
    if per_call is not None:
        settings.HOUSTON_BRAIN_PER_CALL_INPUT_TOKENS = per_call
    if total is not None:
        settings.HOUSTON_BRAIN_TOTAL_INPUT_TOKENS = total
    establishment = create_establishment(name=f"Brain run {uuid.uuid4().hex[:8]}")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    reporting = _reporting(establishment, owner.user)
    extraction = reporting.extractions.get()
    extraction.payload = {
        "measures": [],
        "qualitative": [
            {
                "kind": "paragraph",
                "text": text,
                "locator": {"block": index},
            }
            for index, text in enumerate(texts)
        ],
    }
    extraction.save(update_fields=["payload", "updated_at"])
    return _admit(owner.user, establishment, reporting, key=uuid.uuid4().hex)
