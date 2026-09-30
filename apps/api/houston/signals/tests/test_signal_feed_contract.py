from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.signals.exceptions import SignalPinLimitError
from houston.signals.models import Signal
from houston.signals.services import mark_signal_interesting, pin_signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    login,
    signal_detail_url,
    signal_feed_url,
)
from houston.testing.auth import build_api_membership_on_establishment
from houston.testing.taxonomy import (
    create_activity_subject,
    create_business_unit,
    create_membership_with_business_unit_scope,
    create_signal_v3_for_membership,
)

pytestmark = pytest.mark.django_db


def _pin(signal, membership):
    signal.is_pinned = True
    signal.pinned_at = signal.created_at
    signal.pinned_by_membership = membership
    signal.save(update_fields=["is_pinned", "pinned_at", "pinned_by_membership", "updated_at"])
    return signal


def _feed(api_client, membership, query: str):
    token = login(api_client, user=membership.user)
    return api_client.get(
        signal_feed_url(membership.establishment_id) + query,
        **auth_headers(token),
    )


def test_si01_resolve_clears_pin_and_keeps_signal_until_retention_ends(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _pin(create_minimal_v3_signal(membership, title="Pinned open"), membership)
    token = login(api_client, user=membership.user)

    resolved = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )
    assert resolved.status_code == 200

    feed = _feed(api_client, membership, "?view_mode=general")
    body = feed.json()
    assert feed.status_code == 200
    assert [item["id"] for item in body["items"]] == [str(signal.id)]
    assert body["items"][0]["status"] == Signal.Status.RESOLVED
    assert body["pins"] == []
    assert body["counts"]["open"] == 0
    assert body["counts"]["pinned"] == 0
    assert body["counts"]["retained"] == 1
    assert (
        body["counts"]["open"]
        + body["counts"]["in_progress"]
        + body["counts"]["interesting"]
        + body["counts"]["pinned"]
        + body["counts"]["retained"]
        == len(body["items"]) + len(body["pins"])
    )

    detail = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == Signal.Status.RESOLVED
    assert detail.json()["is_pinned"] is False


def test_si02_open_to_interesting_keeps_pin_and_respects_filter(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _pin(create_minimal_v3_signal(membership, title="Keep pin"), membership)
    mark_signal_interesting(signal=signal, actor_membership=membership)

    overall = _feed(api_client, membership, "?view_mode=general").json()
    assert [item["id"] for item in overall["pins"]] == [str(signal.id)]
    assert overall["items"] == []
    assert overall["counts"]["interesting"] == 0
    assert overall["counts"]["pinned"] == 1

    interesting = _feed(api_client, membership, "?view_mode=general&statuses=interesting").json()
    assert [item["id"] for item in interesting["pins"]] == [str(signal.id)]
    assert interesting["items"] == []
    assert interesting["counts"]["pinned"] == 1

    opened = _feed(api_client, membership, "?view_mode=general&statuses=open").json()
    assert opened["pins"] == []
    assert opened["items"] == []
    assert opened["counts"]["pinned"] == 0
    assert opened["counts"]["interesting"] == 0


def test_si03_in_progress_removes_pin_and_increases_in_progress_count(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Will progress")
    pin_signal(signal=signal, membership=membership)
    pilot = signal.responsible_business_unit
    assert pilot is not None
    create_action_plan_with_execution(
        establishment_id=membership.establishment_id,
        created_by=membership,
        pilot_business_unit_id=pilot.id,
        title="Start work",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Follow up", business_unit=pilot)],
        assignees=[build_assignee_payload(membership=membership, business_unit=pilot)],
    )

    body = _feed(api_client, membership, "?view_mode=general").json()
    assert body["pins"] == []
    assert [item["id"] for item in body["items"]] == [str(signal.id)]
    assert body["counts"]["in_progress"] == 1
    assert body["counts"]["pinned"] == 0
    assert body["counts"]["open"] == 0
    signal.refresh_from_db()
    assert signal.is_pinned is False
    assert signal.status == Signal.Status.IN_PROGRESS


def test_si06_global_page_then_direct_status(api_client):
    membership = build_api_membership()
    opens = [create_minimal_v3_signal(membership, title=f"Open {index}") for index in range(3)]
    progress = create_minimal_v3_signal(
        membership,
        title="Progress",
        status=Signal.Status.IN_PROGRESS,
    )

    first = _feed(api_client, membership, "?view_mode=general&page_size=2")
    assert first.status_code == 200
    first_body = first.json()
    assert [item["status"] for item in first_body["items"]] == ["open", "open"]
    assert first_body["has_more"] is True
    assert "counts" in first_body
    assert first_body["counts"]["open"] == 3
    assert first_body["counts"]["in_progress"] == 1

    second = _feed(
        api_client,
        membership,
        f"?view_mode=general&page_size=2&cursor={first_body['next_cursor']}",
    )
    assert second.status_code == 200
    second_body = second.json()
    assert [item["status"] for item in second_body["items"]] == ["open", "in_progress"]
    assert second_body["has_more"] is False
    assert "counts" not in second_body
    seen = {item["id"] for item in first_body["items"]} | {
        item["id"] for item in second_body["items"]
    }
    assert seen == {str(signal.id) for signal in opens} | {str(progress.id)}

    direct = _feed(api_client, membership, "?view_mode=general&statuses=in_progress")
    assert [item["id"] for item in direct.json()["items"]] == [str(progress.id)]


def test_ct02_interesting_filter_stays_usable_when_only_pins_match(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pinned = _pin(
        create_minimal_v3_signal(
            membership,
            title="Pinned interesting",
            status=Signal.Status.INTERESTING,
        ),
        membership,
    )

    body = _feed(api_client, membership, "?view_mode=general&statuses=interesting").json()
    assert body["counts"]["interesting"] == 0
    assert body["counts"]["pinned"] == 1
    assert body["items"] == []
    assert [item["id"] for item in body["pins"]] == [str(pinned.id)]


def test_ct03_pin_cap_is_establishment_wide_across_filters(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    pinned = []
    for index in range(5):
        signal = create_minimal_v3_signal(membership, title=f"Open pin {index}")
        pin_signal(signal=signal, membership=membership)
        pinned.append(signal)
    extra = create_minimal_v3_signal(
        membership,
        title="Interesting extra",
        status=Signal.Status.INTERESTING,
    )
    token = login(api_client, user=membership.user)

    blocked = api_client.post(
        signal_detail_url(membership.establishment_id, extra.id) + "pin/",
        **auth_headers(token),
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "signal_pin_limit"
    assert (
        Signal.objects.filter(establishment_id=membership.establishment_id, is_pinned=True).count()
        == 5
    )

    replaced = api_client.post(
        signal_detail_url(membership.establishment_id, extra.id) + "pin/",
        data={"replace_pin_id": str(pinned[0].id)},
        format="json",
        **auth_headers(token),
    )
    assert replaced.status_code == 200
    pinned[0].refresh_from_db()
    extra.refresh_from_db()
    assert pinned[0].is_pinned is False
    assert extra.is_pinned is True
    assert (
        Signal.objects.filter(establishment_id=membership.establishment_id, is_pinned=True).count()
        == 5
    )


def test_si04_pin_moves_between_collections_without_duplicate(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Movable")
    token = login(api_client, user=membership.user)

    before = _feed(api_client, membership, "?view_mode=general").json()
    assert [item["id"] for item in before["items"]] == [str(signal.id)]
    assert before["pins"] == []
    assert before["counts"]["open"] == 1
    assert before["counts"]["pinned"] == 0

    pinned = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "pin/",
        **auth_headers(token),
    )
    assert pinned.status_code == 200
    after_pin = _feed(api_client, membership, "?view_mode=general").json()
    assert after_pin["items"] == []
    assert [item["id"] for item in after_pin["pins"]] == [str(signal.id)]
    assert after_pin["counts"]["open"] == 0
    assert after_pin["counts"]["pinned"] == 1

    unpinned = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "unpin/",
        **auth_headers(token),
    )
    assert unpinned.status_code == 200
    after_unpin = _feed(api_client, membership, "?view_mode=general").json()
    assert [item["id"] for item in after_unpin["items"]] == [str(signal.id)]
    assert after_unpin["pins"] == []
    assert after_unpin["counts"]["open"] == 1
    assert after_unpin["counts"]["pinned"] == 0


def test_si05_sixth_pin_requires_explicit_replace():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signals = [create_minimal_v3_signal(membership, title=f"Cap {index}") for index in range(6)]
    for signal in signals[:5]:
        pin_signal(signal=signal, membership=membership)

    with pytest.raises(SignalPinLimitError) as exc_info:
        pin_signal(signal=signals[5], membership=membership)
    assert len(exc_info.value.replacement_candidates) == 5
    assert (
        Signal.objects.filter(is_pinned=True, establishment_id=membership.establishment_id).count()
        == 5
    )

    pin_signal(signal=signals[5], membership=membership, replace_pin_id=signals[0].id)
    signals[0].refresh_from_db()
    signals[5].refresh_from_db()
    assert signals[0].is_pinned is False
    assert signals[5].is_pinned is True


@pytest.mark.django_db(transaction=True)
def test_si05_concurrent_pins_do_not_exceed_cap():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signals = [create_minimal_v3_signal(membership, title=f"Race {index}") for index in range(6)]
    for signal in signals[:4]:
        pin_signal(signal=signal, membership=membership)
    start = Barrier(2)

    def attempt(signal_id):
        close_old_connections()
        try:
            actor = EstablishmentMembership.objects.get(pk=membership.pk)
            target = Signal.objects.get(pk=signal_id)
            start.wait()
            try:
                pin_signal(signal=target, membership=actor)
            except SignalPinLimitError:
                return "limit"
            return "created"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(attempt, [signals[4].id, signals[5].id]))

    assert sorted(outcomes) == ["created", "limit"]
    assert (
        Signal.objects.filter(establishment_id=membership.establishment_id, is_pinned=True).count()
        == 5
    )


def test_rb02_invisible_pins_are_not_leaked_when_cap_blocks_pin(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    visible_unit = create_business_unit(
        establishment=owner.establishment,
        key=f"visible-{owner.establishment_id.hex[:8]}",
        label="Visible pole",
    )
    subject = create_activity_subject(
        establishment=owner.establishment,
        business_unit=visible_unit,
        label="Visible subject",
    )
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(membership=manager, business_unit=visible_unit)
    for index in range(5):
        hidden = create_minimal_v3_signal(owner, title=f"Hidden pin {index}")
        pin_signal(signal=hidden, membership=owner)
    visible = create_signal_v3_for_membership(
        owner,
        affected_business_unit=visible_unit,
        responsible_business_unit=visible_unit,
        activity_subject=subject,
        title="Visible target",
    )
    token = login(api_client, user=manager.user)

    response = api_client.post(
        signal_detail_url(owner.establishment_id, visible.id) + "pin/",
        **auth_headers(token),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["replacement_candidates"] == []
    encoded = response.content.decode()
    assert "Hidden pin" not in encoded
    assert visible.is_pinned is False
    visible.refresh_from_db()
    assert visible.is_pinned is False
    assert (
        Signal.objects.filter(establishment_id=owner.establishment_id, is_pinned=True).count() == 5
    )


def test_cursor_context_mismatch_when_role_changes(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    for index in range(3):
        create_minimal_v3_signal(membership, title=f"Role {index}")
    first = _feed(api_client, membership, "?view_mode=general&page_size=1")
    cursor = first.json()["next_cursor"]
    membership.role = EstablishmentMembership.Role.STAFF
    membership.save(update_fields=["role", "updated_at"])

    replay = _feed(
        api_client,
        membership,
        f"?view_mode=general&page_size=1&cursor={cursor}",
    )
    assert replay.status_code == 400
    assert replay.json()["code"] == "cursor_context_mismatch"


def test_repin_does_not_move_pinned_at():
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, title="Already pinned")
    pin_signal(signal=signal, membership=membership)
    signal.refresh_from_db()
    original = signal.pinned_at
    again = pin_signal(signal=signal, membership=membership)
    assert again.pinned_at == original
    assert again.is_pinned is True
