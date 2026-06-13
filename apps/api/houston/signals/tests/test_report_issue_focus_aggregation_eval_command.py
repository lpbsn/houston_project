from __future__ import annotations

import json
from io import StringIO

import pytest
from django.core.management import call_command

from houston.establishments.tests.taxonomy_helpers import (
    create_activity_subject,
    create_business_unit,
)
from houston.testing.factories import build_membership
from houston.testing.taxonomy import create_v3_signal

pytestmark = pytest.mark.django_db


def test_report_issue_focus_aggregation_eval_json_output():
    membership = build_membership()
    establishment = membership.establishment
    bar = create_business_unit(establishment=establishment, key="bar", label="Bar")
    stock = create_activity_subject(
        establishment=establishment,
        business_unit=bar,
        label="Stock",
    )
    create_v3_signal(
        establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=stock,
        title="Rupture pain",
        structured_summary="Plus de pain.",
        issue_focus="pain",
    )
    create_v3_signal(
        establishment,
        affected_business_unit=bar,
        responsible_business_unit=bar,
        activity_subject=stock,
        title="Rupture mojito",
        structured_summary="Plus de sirop mojito.",
        issue_focus="sirop mojito",
    )

    buffer = StringIO()
    call_command(
        "report_issue_focus_aggregation_eval",
        establishment_id=str(establishment.id),
        json=True,
        stdout=buffer,
    )
    payload = json.loads(buffer.getvalue())

    assert payload["establishment_id"] == str(establishment.id)
    assert payload["taxonomy_duplicate_group_count"] == 1
    assert payload["lot4bis_trigger_indicators"]["numerous_taxonomy_duplicate_groups"] is False
