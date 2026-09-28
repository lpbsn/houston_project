from __future__ import annotations

import pytest

from houston.core.feed_hardening_baseline import (
    _delete_feed_baseline_dataset,
    resolve_feed_baseline_profile,
)
from houston.notifications.models import Notification


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("establishments", "establishments must be positive"),
        ("signals_per_establishment", "signals_per_establishment must be at least 30"),
        ("executions_per_establishment", "executions_per_establishment must be at least 30"),
    ],
)
def test_explicit_zero_reaches_baseline_profile_validation(field, message):
    with pytest.raises(ValueError, match=message):
        resolve_feed_baseline_profile("smoke", **{field: 0})


@pytest.mark.django_db
def test_delete_feed_baseline_dataset_deletes_notifications_once(monkeypatch):
    delete_calls = 0
    original_filter = Notification.objects.filter

    def counting_filter(*args, **kwargs):
        queryset = original_filter(*args, **kwargs)
        original_delete = queryset.delete

        def counting_delete(*delete_args, **delete_kwargs):
            nonlocal delete_calls
            delete_calls += 1
            return original_delete(*delete_args, **delete_kwargs)

        queryset.delete = counting_delete
        return queryset

    monkeypatch.setattr(Notification.objects, "filter", counting_filter)

    _delete_feed_baseline_dataset()

    assert delete_calls == 1
